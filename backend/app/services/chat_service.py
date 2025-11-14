import json
import re
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

from dateparser.date import DateDataParser
from dateparser.search import search_dates

from openai import RateLimitError

# Common timezone abbreviations and their UTC offsets
TIMEZONE_OFFSETS = {
    "est": -5,  # Eastern Standard Time (UTC-5)
    "edt": -4,  # Eastern Daylight Time (UTC-4)
    "cst": -6,  # Central Standard Time (UTC-6)
    "cdt": -5,  # Central Daylight Time (UTC-5)
    "mst": -7,  # Mountain Standard Time (UTC-7)
    "mdt": -6,  # Mountain Daylight Time (UTC-6)
    "pst": -8,  # Pacific Standard Time (UTC-8)
    "pdt": -7,  # Pacific Daylight Time (UTC-7)
    "gmt": 0,   # Greenwich Mean Time (UTC+0)
    "utc": 0,   # Coordinated Universal Time (UTC+0)
    "ist": 5.5, # Indian Standard Time (UTC+5:30)
}

from app.config import (
    FALLBACK_MODELS,
    MAX_SEARCH_LIMIT,
    MAX_STREAMING_TOKENS,
    SIMILARITY_SCORE,
    TEMPERATURE,
    get_async_openai_client,
    get_fallback_api_key,
    get_redis_client,
    get_supabase_client,
    setup_logger,
)
from app.services.document_service import (
    search_similar_documents,
    summarize_text,
)
from app.services.summary_service import SummaryService


logger = setup_logger("chat-service")


class ChatService:
    def __init__(self, active_generations: dict[str, bool] = None):
        self.openai_client = get_async_openai_client()
        self.supabase = get_supabase_client()
        self.redis_client = get_redis_client()
        self.active_generations = active_generations or {}
        self.summary_service = SummaryService()
        self.date_parser = DateDataParser(
            languages=["en"],
            settings={
                "PREFER_DATES_FROM": "past",
                "RETURN_AS_TIMEZONE_AWARE": True,
            },
        )

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _start_of_day(self, dt: datetime) -> datetime:
        dt_utc = self._ensure_utc(dt)
        return dt_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    def _end_of_day(self, dt: datetime) -> datetime:
        dt_utc = self._ensure_utc(dt)
        # Use start of next day minus 1 microsecond to ensure we capture all of the day
        next_day = dt_utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return next_day - timedelta(microseconds=1)

    def _parse_time(self, time_str: str) -> tuple[int, int, int | float] | None:
        """
        Parse time string like '2pm', '14:30', '9:00am EST' into (hour, minute, timezone_offset).
        Returns (hour, minute, timezone_offset) where timezone_offset is in hours from UTC.
        If no timezone is specified, returns offset of 0 (assumes UTC).
        """
        time_str = time_str.strip().lower()
        timezone_offset = 0  # Default to UTC
        
        # Extract timezone abbreviation if present
        tz_match = re.search(r"\b([a-z]{3,4})\b", time_str)
        if tz_match:
            tz_abbr = tz_match.group(1)
            if tz_abbr in TIMEZONE_OFFSETS:
                timezone_offset = TIMEZONE_OFFSETS[tz_abbr]
                # Remove timezone from string for time parsing
                time_str = re.sub(r"\b" + tz_abbr + r"\b", "", time_str).strip()
        
        # Handle 12-hour format with am/pm
        am_pm_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", time_str)
        if am_pm_match:
            hour = int(am_pm_match.group(1))
            minute = int(am_pm_match.group(2) or "0")
            period = am_pm_match.group(3)
            
            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0
            
            return (hour, minute, timezone_offset)
        
        # Handle 24-hour format (HH:MM or HHMM)
        time_match = re.search(r"(\d{1,2}):?(\d{2})", time_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return (hour, minute, timezone_offset)
        
        return None

    def _apply_time_to_datetime(self, dt: datetime, hour: int, minute: int, timezone_offset: int | float = 0) -> datetime:
        """
        Apply time to a datetime object, converting from specified timezone to UTC.
        
        Args:
            dt: Base datetime object
            hour: Hour in the specified timezone
            minute: Minute in the specified timezone
            timezone_offset: Timezone offset in hours from UTC (e.g., -5 for EST)
                            Negative values mean behind UTC, positive means ahead
        
        Returns:
            Datetime object in UTC
        """
        dt_utc = self._ensure_utc(dt)
        # Create datetime with the specified time in the local timezone
        local_dt = dt_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Convert to UTC by subtracting the timezone offset
        # If offset is -5 (EST), we subtract -5 = add 5 hours to get UTC
        if timezone_offset != 0:
            offset_hours = int(timezone_offset)
            offset_minutes = int((timezone_offset - offset_hours) * 60)
            # Subtract negative offset = add hours (e.g., -(-5) = +5)
            local_dt = local_dt - timedelta(hours=offset_hours, minutes=offset_minutes)
        
        return local_dt

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 800) -> list[str]:
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    def _parse_with_dateparser(
        self, message: str, now: datetime
    ) -> dict | None:
        settings = {
            "RELATIVE_BASE": now,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "past",
        }

        try:
            matches = search_dates(message, settings=settings) or []
        except Exception:
            matches = []

        if matches:
            datetimes = sorted(
                {self._ensure_utc(dt) for _, dt in matches},
                key=lambda value: value,
            )

            if len(datetimes) >= 2:
                start = self._start_of_day(datetimes[0])
                end = self._end_of_day(datetimes[-1])
            else:
                dt = datetimes[0]
                lowered = message.lower()

                if re.search(r"\bsince\b|\bafter\b", lowered):
                    start = self._start_of_day(dt)
                    end = self._end_of_day(now)
                elif re.search(r"\buntil\b|\btill\b|\bthrough\b|\bby\b", lowered):
                    start = self._start_of_day(dt)
                    end = self._end_of_day(dt)
                else:
                    start = self._start_of_day(dt)
                    end = self._end_of_day(dt)

            return {
                "start_iso": start.isoformat(),
                "end_iso": end.isoformat(),
                "display_start": start.strftime("%Y-%m-%d"),
                "display_end": end.strftime("%Y-%m-%d"),
            }

        try:
            data = self.date_parser.get_date_data(message)
        except Exception:
            return None

        dt = data.get("date_obj")
        period = data.get("period")
        if not dt:
            return None

        dt = self._ensure_utc(dt)
        period = (period or "day").lower()

        if period == "week":
            end_date = self._end_of_day(dt)
            start_date = self._start_of_day(dt - timedelta(days=6))
        elif period == "month":
            start_base = dt.replace(day=1)
            if start_base.month == 12:
                next_month = start_base.replace(year=start_base.year + 1, month=1)
            else:
                next_month = start_base.replace(month=start_base.month + 1)
            end_base = next_month - timedelta(days=1)
            start_date = self._start_of_day(start_base)
            end_date = self._end_of_day(end_base)
        elif period == "quarter":
            quarter_index = (dt.month - 1) // 3
            start_month = quarter_index * 3 + 1
            start_base = dt.replace(month=start_month, day=1)
            if start_month == 10:
                next_quarter = start_base.replace(year=start_base.year + 1, month=1)
            else:
                next_quarter = start_base.replace(month=start_month + 3)
            end_base = next_quarter - timedelta(days=1)
            start_date = self._start_of_day(start_base)
            end_date = self._end_of_day(end_base)
        elif period == "year":
            start_base = dt.replace(month=1, day=1)
            end_base = start_base.replace(year=start_base.year + 1) - timedelta(
                days=1
            )
            start_date = self._start_of_day(start_base)
            end_date = self._end_of_day(end_base)
        else:
            start_date = self._start_of_day(dt)
            end_date = self._end_of_day(dt)

        return {
            "start_iso": start_date.isoformat(),
            "end_iso": end_date.isoformat(),
            "display_start": start_date.strftime("%Y-%m-%d"),
            "display_end": end_date.strftime("%Y-%m-%d"),
        }

    def _parse_summary_request(self, message: str) -> dict | None:
        text = message.lower()

        if not re.search(r"\bsummar(?:ize|y)\b", text):
            return None

        now = datetime.now(timezone.utc)
        start = end = None
        parsed_date = None

        # Step 1: Try to extract any date from the message (including natural language)
        # First try numeric date formats
        if match := re.search(
            r"(?:from|between|on)\s+(\d{4}-\d{2}-\d{2})\s+(?:to|-|through|and)\s+(\d{4}-\d{2}-\d{2})",
            text,
            re.IGNORECASE,
        ):
            try:
                start_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                end_date = datetime.strptime(match.group(2), "%Y-%m-%d")
                parsed_date = {"start": start_date, "end": end_date, "type": "range"}
            except ValueError:
                pass
        elif match := re.search(r"(\d{4}-\d{2}-\d{2})", text):
            try:
                single_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                parsed_date = {"start": single_date, "end": single_date, "type": "single"}
            except ValueError:
                pass

        # If no numeric date found, try natural language date parsing
        if not parsed_date:
            # First, try to extract explicit date patterns like "on November 11 2025" or "November 11 2025"
            # This is more precise than search_dates which might find multiple dates
            explicit_date_patterns = [
                r"(?:on|uploaded\s+on)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",  # "on November 11, 2025" or "on November 11 2025"
                r"([A-Za-z]+\s+\d{1,2},?\s+\d{4})",  # "November 11, 2025" or "November 11 2025"
                r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",  # "11 November 2025"
            ]
            
            for pattern in explicit_date_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    try:
                        # Try parsing with dateparser
                        data = self.date_parser.get_date_data(date_str)
                        dt = data.get("date_obj")
                        if dt:
                            dt = self._ensure_utc(dt)
                            parsed_date = {
                                "start": dt,
                                "end": dt,
                                "type": "single",
                            }
                            break
                    except Exception:
                        continue
            
            # If still no date found, try search_dates as fallback
            if not parsed_date:
                try:
                    # Use search_dates to find all date mentions
                    settings = {
                        "RELATIVE_BASE": now,
                        "RETURN_AS_TIMEZONE_AWARE": True,
                        "PREFER_DATES_FROM": "past",
                    }
                    matches = search_dates(message, settings=settings) or []
                    
                    if matches:
                        # Filter to only use dates that look like explicit date mentions
                        # Prefer dates that are near "on", "uploaded", or similar context words
                        filtered_matches = []
                        for text_part, dt in matches:
                            # Check if this date is near context words that suggest it's the intended date
                            text_lower = message.lower()
                            idx = text_lower.find(text_part.lower())
                            if idx != -1:
                                # Check surrounding context
                                context_start = max(0, idx - 20)
                                context_end = min(len(text_lower), idx + len(text_part) + 20)
                                context = text_lower[context_start:context_end]
                                
                                # If near "on", "uploaded", or date-like words, prefer it
                                if any(word in context for word in ["on", "uploaded", "november", "december", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october"]):
                                    filtered_matches.append((text_part, dt))
                        
                        # Use filtered matches if available, otherwise use all
                        matches_to_use = filtered_matches if filtered_matches else matches
                        
                        if matches_to_use:
                            datetimes = sorted(
                                {self._ensure_utc(dt) for _, dt in matches_to_use},
                                key=lambda value: value,
                            )
                            # If multiple dates found, use the first one (most likely the intended date)
                            # Only create a range if there are clearly two distinct dates
                            if len(datetimes) >= 2 and abs((datetimes[-1] - datetimes[0]).days) > 1:
                                parsed_date = {
                                    "start": datetimes[0],
                                    "end": datetimes[-1],
                                    "type": "range",
                                }
                            else:
                                # Use the first (or only) date found
                                parsed_date = {
                                    "start": datetimes[0],
                                    "end": datetimes[0],
                                    "type": "single",
                                }
                except Exception:
                    pass

        # Step 2: Try to extract time range (including timezone if specified)
        # Look for timezone at the end of the time range or after each time
        time_range_match = re.search(
            r"(?:between|from)\s+(\d{1,2}:?\d{0,2}(?:\s*(?:am|pm))?(?:\s+[a-z]{3,4})?)\s+(?:and|to|-)\s+(\d{1,2}:?\d{0,2}(?:\s*(?:am|pm))?(?:\s+[a-z]{3,4})?)",
            text,
            re.IGNORECASE,
        )
        
        start_time = None
        end_time = None
        if time_range_match:
            start_time_str = time_range_match.group(1).strip()
            end_time_str = time_range_match.group(2).strip()
            start_time = self._parse_time(start_time_str)
            end_time = self._parse_time(end_time_str)
            
            # If timezone not found in individual times, check if it's specified at the end of the range
            if start_time and end_time and start_time[2] == 0 and end_time[2] == 0:
                # Look for timezone after the time range
                tz_after_match = re.search(
                    r"(?:between|from)\s+\d{1,2}:?\d{0,2}(?:\s*(?:am|pm))?\s+(?:and|to|-)\s+\d{1,2}:?\d{0,2}(?:\s*(?:am|pm))?\s+([a-z]{3,4})\b",
                    text,
                    re.IGNORECASE,
                )
                if tz_after_match:
                    tz_abbr = tz_after_match.group(1).lower()
                    if tz_abbr in TIMEZONE_OFFSETS:
                        tz_offset = TIMEZONE_OFFSETS[tz_abbr]
                        # Update both times with the timezone offset
                        start_time = (start_time[0], start_time[1], tz_offset)
                        end_time = (end_time[0], end_time[1], tz_offset)

        # Step 3: Combine date and time
        if parsed_date:
            base_start = parsed_date["start"]
            base_end = parsed_date["end"]
            
            if start_time and end_time:
                # Apply time to the date(s)
                start = self._apply_time_to_datetime(base_start, *start_time)
                if parsed_date["type"] == "range":
                    end = self._apply_time_to_datetime(base_end, *end_time)
                else:
                    end = self._apply_time_to_datetime(base_start, *end_time)
                    # If end time is before start time on same day, assume next day
                    if end < start:
                        end = end + timedelta(days=1)
            else:
                # No time specified, use full day(s)
                start = self._start_of_day(base_start)
                if parsed_date["type"] == "range":
                    end = self._end_of_day(base_end)
                else:
                    end = self._end_of_day(base_start)
        elif start_time and end_time:
            # Time range but no date - apply to today or check for relative dates
            base_date = now
            if "yesterday" in text:
                base_date = now - timedelta(days=1)
            elif "today" in text:
                base_date = now
            
            start = self._apply_time_to_datetime(base_date, *start_time)
            end = self._apply_time_to_datetime(base_date, *end_time)
            if end < start:
                end = end + timedelta(days=1)

        # Step 4: Fallback to other date patterns if nothing found yet
        if not (start and end):
            if match := re.search(r"last\s+(\d+)\s*(day|days)", text):
                days = int(match.group(1))
                end = self._end_of_day(now)
                start = self._start_of_day(now - timedelta(days=days))
            elif re.search(r"last\s+week|past\s+week", text):
                end = self._end_of_day(now)
                start = self._start_of_day(now - timedelta(days=7))
            elif re.search(r"last\s+month|past\s+month", text):
                end = self._end_of_day(now)
                start = self._start_of_day(now - timedelta(days=30))
            elif "yesterday" in text:
                target = now - timedelta(days=1)
                start = self._start_of_day(target)
                end = self._end_of_day(target)
            elif "today" in text:
                start = self._start_of_day(now)
                end = self._end_of_day(now)
            else:
                # Final fallback to dateparser
                parsed = self._parse_with_dateparser(message, now)
                if parsed:
                    start = datetime.fromisoformat(parsed["start_iso"])
                    end = datetime.fromisoformat(parsed["end_iso"])
                    
                    # Check if there's a time range to apply
                    if start_time and end_time:
                        start = self._apply_time_to_datetime(start, *start_time)
                        end = self._apply_time_to_datetime(end, *end_time)

        if not (start and end):
            return None

        # Format display strings with time if applicable
        # Check if this is a full day range (start at 00:00:00 and end at end of day)
        # End of day will be 23:59:59.999999 or start of next day minus 1 microsecond
        is_full_day = (
            start.hour == 0 
            and start.minute == 0 
            and start.second == 0
            and start.microsecond == 0
            and (
                (end.hour == 23 and end.minute == 59) 
                or (end.hour == 0 and end.minute == 0 and end.second == 0 and end.microsecond < 1000)
            )
            and start.date() == end.date()
        )
        
        if is_full_day:
            # Full day range, show date only
            display_start = start.strftime("%Y-%m-%d")
            display_end = end.strftime("%Y-%m-%d")
        else:
            # Include time in display
            display_start = start.strftime("%Y-%m-%d %H:%M")
            display_end = end.strftime("%Y-%m-%d %H:%M")

        return {
            "start_iso": start.isoformat(),
            "end_iso": end.isoformat(),
            "display_start": display_start,
            "display_end": display_end,
        }

    async def _generate_time_range_summary(
        self, user_id: str, message: str, window: dict
    ) -> str:
        try:
            logger.info(
                f"Generating summary for user {user_id} with time range: "
                f"{window['start_iso']} to {window['end_iso']}"
            )
            result = await self.summary_service.generate_summary(
                user_id=user_id,
                start_date=window["start_iso"],
                end_date=window["end_iso"],
            )
            summary_body = (result.get("summary") or "").strip()
            if not summary_body:
                summary_body = "_No content returned by the summarization model._"

            header = (
                "### Document summary\n"
                f"- Time Range (UTC): {window['display_start']} → {window['display_end']}\n"
                f"- Documents covered: {result.get('document_count', 0)}\n\n"
            )
            return header + summary_body
        except ValueError as e:
            logger.warning(
                f"No documents found for user {user_id} between "
                f"{window['start_iso']} and {window['end_iso']}: {str(e)}"
            )
            return (
                f"I couldn't find any documents between "
                f"{window['display_start']} and {window['display_end']}.\n\n"
                f"**Note:** Times are in UTC. If you specified a local time, "
                f"please account for your timezone offset."
            )
        except Exception as exc:
            logger.error(
                f"Failed summary generation for user {user_id}: {str(exc)}"
            )
            return (
                "I'm having trouble generating that summary right now. "
                "Please try again later."
            )

    async def get_relevant_context(
        self,
        query: str,
        user_id: str,
        max_results: int = MAX_SEARCH_LIMIT,
        similarity: float = SIMILARITY_SCORE,
    ) -> str | None:
        try:
            result = await search_similar_documents(
                user_id, query, max_results, similarity
            )

            if not result:
                logger.info("No relevant documents found")
                return

            context_parts = []
            chunk_ids, document_ids = set(), set()

            for i, data in enumerate(result):
                content = data.get("content", "")
                title = data.get("title", "")
                chunk_ids.add(data.get("chunk_id", ""))
                document_ids.add(data.get("document_id", ""))
                context_parts.append(
                    f"Document '{title}' - Section {i+1}: {content}"
                )

            logger.info(
                f"Found {len(chunk_ids)} relevant chunks from {len(set(document_ids))} documents"
            )
            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(
                f"Error retrieving context for user {user_id}: {str(e)}"
            )
            return

    @staticmethod
    async def get_chat_stream(client, model, messages, should_stop=None):
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            max_tokens=MAX_STREAMING_TOKENS,
            temperature=TEMPERATURE,
        )

        async for chunk in stream:
            if should_stop and should_stop():
                break
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                yield content

    async def generate_streaming_response(
        self,
        user_id: str,
        message: str,
        session_id: str = None,
        message_id: str = None,
    ) -> AsyncGenerator[str]:
        full_response = ""
        try:
            summary_window = self._parse_summary_request(message)
            if summary_window:
                summary_text = await self._generate_time_range_summary(
                    user_id, message, summary_window
                )
                full_response = summary_text
                for chunk in self._chunk_text(summary_text):
                    yield chunk
                await self.save_conversation(user_id, message, summary_text)
                return

            logger.info(
                f"Retrieving context for user {user_id} with query: {message}"
            )

            if session_id:
                context = await self.get_session_document_context(
                    session_id, message, user_id
                )
                history = await self.get_session_conversation_history(
                    session_id, user_id
                )
                conversation_context = (
                    await self.build_conversation_context_from_history(history)
                )
            else:
                context = await self.get_relevant_context(message, user_id)
                conversation_context = await self.get_conversation_context(
                    user_id
                )

            system_prompt = f"""
            You are a helpful AI Chatbot designed primarily for Question and Answering.
            Your task is to answer questions based on the user's uploaded documents and previous conversation context.

            Use the following context from the user's document library to answer questions.
            Context from user's documents:
            {context}

            {conversation_context}

            Instructions:
            1). Primary Source:
                - Base your answers strictly on the provided context.
                - If a clear answer exists in the context, respond concisely but thoroughly.

                When Context Is Insufficient:
                - If the answer is not present in the context, check if it is a universally true fact (e.g., "The sun rises in the east").
                - If so, provide the general truth clearly and politely.
                - Otherwise, refrain from answering, and say something like: "I'm sorry, but I couldn't find any relevant information in the provided documents."

            2). Tone and Style:
                - ALWAYS maintain a polite, respectful, and professional tone.
                - AVOID speculation, assumptions, or unverifiable claims.
                - Write in clear, grammatically correct English.
                - Keep your answers short and to the point. Be concise and direct.

            3). Formatting:
                - Use brief paragraphs and Markdown for readability (headings, lists, etc.).
                - Highlight important terms (like numbers, dates, answers) only if it improves clarity.
                - When presenting numerical values, use appropriate formatting:
                  * For large numbers, use scientific notation or abbreviations (e.g., "1.39 × 10^12" or "1.39 trillion")
                  * Limit decimal places to 2-3 significant digits maximum
                  * NEVER output extremely long decimal numbers with hundreds of digits

"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]
            logger.info(
                f"Starting streaming response generation for user {user_id}"
            )

            clients_available = []
            for model, api_key_name in FALLBACK_MODELS:
                api_key = get_fallback_api_key(api_key_name)
                if api_key:
                    clients_available.append(
                        (get_async_openai_client(api_key), model)
                    )

            for client, model in clients_available:
                try:
                    logger.info(f"Trying: {model}")

                    def should_stop():
                        return (
                            not self.active_generations.get(message_id, True)
                            if message_id
                            else False
                        )

                    async for content in self.get_chat_stream(
                        client, model, messages, should_stop
                    ):
                        full_response += content
                        yield content

                    break

                except RateLimitError as e:
                    if e.status_code == 429:
                        logger.warning(
                            f"Rate limit hit, trying fallback models for user {user_id}"
                        )
                        continue

                    else:
                        raise
                except Exception as e:
                    raise e
            else:
                error = "I'm having trouble generating a response right now. All models are rate limited."
                full_response = error
                yield error

            if full_response.strip():
                await self.save_conversation(
                    user_id, message, full_response.strip()
                )

        except Exception as e:
            logger.error(
                f"Error in generating streaming response for user {user_id}: {str(e)}"
            )
            error = "I'm having trouble generating a response right now"
            await self.save_conversation(user_id, message, error)
            yield error

    async def get_conversation_history(
        self, user_id: str, limit: int = 10
    ) -> list[dict]:
        try:
            supabase = await get_supabase_client()
            result = await (
                supabase.table("conversation_history")
                .select("message, response, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return list(reversed(result.data))
        except Exception as e:
            logger.error(
                f"Error fetching conversation history for user {user_id}: {str(e)}"
            )
            return []

    async def save_conversation(
        self, user_id: str, message: str, response: str
    ):
        try:
            supabase = await get_supabase_client()
            await (
                supabase.table("conversation_history")
                .insert(
                    {
                        "user_id": user_id,
                        "message": message,
                        "response": response,
                    }
                )
                .execute()
            )
        except Exception as e:
            logger.error(
                f"Error saving conversation for user {user_id}: {str(e)}"
            )

    async def get_conversation_context(self, user_id: str) -> str:
        instructions = """
        You are a summarizing agent. Your task is to produce a detailed summary of a dialogue between two speakers (typically an agent and a user) in such a way that it can serve as meaningful context for continuing or initiating further exchanges between them.
        You must create two separate summaries, one for each speaker. Each summary should be written as a coherent paragraph of NOT MORE THAN 500 WORDS, ensuring that all important keywords, questions, and answers (Q&A), significant figures like dates
        metrics, etc. are captured accurately without losing the original context, tone, or intent of the dialogue.
        Your goal is not just to compress the conversation but to preserve its flow, reasoning, and emotional undertones, highlighting the key points, arguments, and responses exchanged between the speakers.

        EXAMPLE:

        Given below is a conversation between two users discussing a research paper.

        USER: They asked several critical questions about the algorithm
        and its underlying mathematics, referencing their expertise in the field.
        They also expressed skepticism about the validity of the reported results, challenging the credibility of the conclusions presented in the paper.
        In some parts of the discussion, they appeared unconvinced by the responses, suggesting that they are analytical and not easily persuaded.

        AI: They responded politely and thoughtfully, addressing each technical question with detailed explanations and examples.
        They clarified the rationale behind the algorithm’s design, defended the experimental results with supporting evidence, and acknowledged the user’s concerns where appropriate.
        The tone remained respectful and professional throughout, showing a willingness to engage in constructive debate and maintain intellectual rigor.
        """
        try:
            history = await self.get_conversation_history(user_id, limit=20)
            if not history:
                return ""

            context_parts = []
            for entry in history:
                context_parts.append(f"User: {entry['message']}")
                context_parts.append(f"Assistant: {entry['response']}")

            conversation_text = "\n".join(context_parts)

            if len(conversation_text) > 400000:
                logger.info("Compacting..", "BLUE")
                summary = await summarize_text(conversation_text, instructions)
                return f"Previous conversation summary: {summary}"

            return f"Previous conversation:\n{conversation_text}"

        except Exception as e:
            logger.error(
                f"Error building conversation context for user {user_id}: {str(e)}"
            )
            return ""

    async def build_conversation_context_from_history(
        self, history: list[dict]
    ) -> str:
        if not history:
            return ""

        context_parts = []
        for entry in history:
            context_parts.append(f"User: {entry['message']}")
            context_parts.append(f"Assistant: {entry['response']}")

        conversation_text = "\n".join(context_parts)
        return f"Previous conversation:\n{conversation_text}"

    def get_cache_key(
        self, prefix: str, session_id: str, suffix: str = ""
    ) -> str:
        return f"{prefix}:{session_id}" + (f":{suffix}" if suffix else "")

    async def cache_data(self, key: str, data: any, ttl: int = 3600):
        try:
            self.redis_client.setex(key, ttl, json.dumps(data))
        except Exception as e:
            logger.error(f"Error caching data: {str(e)}")

    async def get_cached_data(self, key: str) -> any:
        try:
            cached_data = self.redis_client.get(key)
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.error(f"Error retrieving cached data: {str(e)}")
            return None

    async def get_session_conversation_history(
        self, session_id: str, user_id: str
    ) -> list[dict]:
        cache_key = self.get_cache_key("conversation", session_id)
        cached_history = await self.get_cached_data(cache_key)

        if cached_history:
            return cached_history

        history = await self.get_conversation_history(user_id)
        await self.cache_data(cache_key, history, 3600)
        return history

    async def get_session_document_context(
        self, session_id: str, query: str, user_id: str
    ) -> str:
        query_hash = str(hash(query))[:10]
        cache_key = self.get_cache_key("doc_context", session_id, query_hash)
        cached_context = await self.get_cached_data(cache_key)

        if cached_context and cached_context.get("query") == query:
            return cached_context.get("context", "")

        context = await self.get_relevant_context(query, user_id)
        if context:
            await self.cache_data(
                cache_key, {"query": query, "context": context}, 1800
            )

        return context or ""

    async def clear_session_cache(self, session_id: str):
        try:
            conv_key = self.get_cache_key("conversation", session_id)
            self.redis_client.delete(conv_key)

            pattern = f"context:{session_id}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Error clearing session cache: {str(e)}")