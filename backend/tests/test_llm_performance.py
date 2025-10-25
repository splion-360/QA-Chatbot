"""
LLM Performance Benchmarking Suite
==================================

Comprehensive testing framework for evaluating Large Language Models across
multiple providers with detailed performance and quality metrics.

Features:
    - Multi-provider support (OpenAI, Anthropic, Groq, Google)
    - Streaming support for accurate TTFT measurements
    - Quality evaluation with relevance scoring
    - Aggregate metrics and statistical analysis
    - JSON export for further analysis

Author: Suriya
Version: 1.0.0
"""

import asyncio
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os 
from pathlib import Path
from pypdf import PdfReader

# Third-party imports
try:
    from openai import OpenAI
    # import anthropic
    # import google.generativeai as genai
    # from groq import Groq
    from dotenv import load_dotenv
except ImportError as e:
    raise ImportError(
        f"Missing required dependencies: {e}. "
        "Install with: pip install openai anthropic google-generativeai groq python-dotenv"
    )

import json
import os


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_benchmark.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Constants
FALLBACK_PHRASES = frozenset([
    "i cannot", "i don't have", "insufficient information",
    "unable to", "i apologize", "i'm sorry", "no data"
])

KEYWORD_MATCH_THRESHOLD = 0.6
QUALITY_PASS_THRESHOLD = 6.0
MIN_RESPONSE_LENGTH = 50
MAX_TOKENS = 500
DEFAULT_TEMPERATURE = 0.7


class ComplexityLevel(str, Enum):
    """Test case complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    EDGE_CASE = "edge_case"


class Provider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "OpenAI"
    ANTHROPIC = "Anthropic"
    GROQ = "Groq"
    GOOGLE = "Google"


@dataclass
class TestCase:
    """
    Structured test case for LLM evaluation.
    
    Attributes:
        id: Unique identifier for the test case
        document: Source document text
        query: Question to ask about the document
        expected_keywords: Keywords that should appear in good responses
        complexity: Difficulty level of the test
    """
    id: str
    document: str
    query: str
    expected_keywords: List[str]
    complexity: ComplexityLevel
    
    def __post_init__(self) -> None:
        """Validate test case after initialization."""
        if not self.document.strip():
            raise ValueError(f"Test case {self.id} has empty document")
        if not self.query.strip():
            raise ValueError(f"Test case {self.id} has empty query")
        if not self.expected_keywords:
            raise ValueError(f"Test case {self.id} has no expected keywords")


@dataclass
class TestResult:
    """
    Comprehensive test result with performance and quality metrics.
    
    Attributes:
        provider: LLM provider name
        model: Model identifier
        test_id: Reference to test case
        complexity: Test complexity level
        
        Performance Metrics:
            first_token_time: Time to first token (TTFT) in seconds
            total_latency: Total response time in seconds
            throughput: Tokens generated per second
            tokens_generated: Total number of tokens in response
        
        Success Metrics:
            success: Whether test completed without errors
            goal_completed: Whether response quality meets threshold
            is_fallback: Whether response was a fallback/refusal
            error_message: Error details if failed
        
        Quality Metrics:
            relevance_score: Response relevance score (0-10)
            contains_expected_keywords: Whether expected keywords are present
            response_length: Character count of response
            response: Actual response text (truncated for storage)
    """
    provider: str
    model: str
    test_id: str
    complexity: str
    
    # Performance metrics
    first_token_time: Optional[float] = None
    total_latency: Optional[float] = None
    throughput: Optional[float] = None
    tokens_generated: Optional[int] = None
    
    # Success metrics
    success: bool = False
    goal_completed: bool = False
    is_fallback: bool = False
    error_message: Optional[str] = None
    
    # Quality metrics
    relevance_score: Optional[float] = None
    contains_expected_keywords: bool = False
    response_length: int = 0
    response: str = ""
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class AggregateMetrics:
    """
    Aggregate metrics across multiple test runs.
    
    Provides statistical summary of model performance.
    """
    provider: str
    model: str
    total_tests: int
    success_rate: float
    goal_completion_rate: float
    fallback_rate: float
    avg_first_token_time: Optional[float]
    avg_latency: Optional[float]
    avg_throughput: Optional[float]
    avg_relevance_score: Optional[float]
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"{self.provider} {self.model}: "
            f"Success={self.success_rate:.1f}%, "
            f"Goal={self.goal_completion_rate:.1f}%, "
            f"Latency={self.avg_latency:.3f}s"
        )


class QualityEvaluator:
    """
    Evaluates LLM response quality based on multiple criteria.
    
    Methods:
        evaluate: Main evaluation method returning relevance score and keyword presence
    """
    
    @staticmethod
    def evaluate(response: str, test_case: TestCase) -> Tuple[float, bool]:
        """
        Evaluate response quality against expected criteria.
        
        Args:
            response: LLM response text
            test_case: Original test case with expected keywords
            
        Returns:
            Tuple of (relevance_score, contains_keywords)
            - relevance_score: Float between 0-10
            - contains_keywords: Boolean indicating if keywords are present
        """
        # Normalize response for comparison
        response_lower = response.lower()
        
        # Check for expected keywords
        keywords_found = sum(
            1 for keyword in test_case.expected_keywords
            if keyword.lower() in response_lower
        )
        total_keywords = len(test_case.expected_keywords)
        
        # Calculate base relevance score
        keyword_ratio = keywords_found / total_keywords if total_keywords > 0 else 0
        relevance_score = keyword_ratio * 10.0
        
        # Check if meets keyword threshold
        contains_keywords = keyword_ratio >= KEYWORD_MATCH_THRESHOLD
        
        # Detect fallback responses (except for edge cases where they're expected)
        has_fallback = any(
            phrase in response_lower for phrase in FALLBACK_PHRASES
        )
        
        if has_fallback and test_case.complexity != ComplexityLevel.EDGE_CASE:
            relevance_score *= 0.5
            logger.warning(f"Detected fallback response for {test_case.id}")
        
        # Length penalty for very short responses
        if len(response) < MIN_RESPONSE_LENGTH:
            relevance_score *= 0.7
            logger.warning(
                f"Short response ({len(response)} chars) for {test_case.id}"
            )
        
        return min(relevance_score, 10.0), contains_keywords


class LLMTester:
    """
    Base class for LLM provider testing with streaming support.
    
    Provides common functionality for measuring performance metrics.
    """
    
    def __init__(self, provider: Provider):
        """
        Initialize LLM tester.
        
        Args:
            provider: Provider enum value
        """
        self.provider = provider
        self.evaluator = QualityEvaluator()
        self.logger = logging.getLogger(f"{__name__}.{provider.value}")
    
    def _create_result(
        self,
        model: str,
        test_case: TestCase,
        start_time: float,
        first_token_time: Optional[float],
        response_text: str,
        token_count: int,
        error: Optional[Exception] = None
    ) -> TestResult:
        """
        Create TestResult from collected metrics.
        
        Args:
            model: Model identifier
            test_case: Original test case
            start_time: Test start timestamp
            first_token_time: Time to first token
            response_text: Complete response
            token_count: Number of tokens generated
            error: Exception if failed
            
        Returns:
            Populated TestResult object
        """
        result = TestResult(
            provider=self.provider.value,
            model=model,
            test_id=test_case.id,
            complexity=test_case.complexity.value if hasattr(test_case.complexity, 'value') else test_case.complexity
        )
        
        if error:
            result.success = False
            result.is_fallback = True
            result.error_message = str(error)
            self.logger.error(f"Test failed for {model}: {error}")
            return result
        
        # Calculate performance metrics
        total_latency = time.time() - start_time
        result.success = True
        result.first_token_time = round(first_token_time, 3) if first_token_time else None
        result.total_latency = round(total_latency, 3)
        result.throughput = (
            round(token_count / total_latency, 2) 
            if total_latency > 0 else 0
        )
        result.tokens_generated = token_count
        
        # Evaluate quality
        relevance_score, has_keywords = self.evaluator.evaluate(
            response_text, test_case
        )
        
        result.relevance_score = round(relevance_score, 2)
        result.contains_expected_keywords = has_keywords
        result.response_length = len(response_text)
        result.response = (
            response_text[:300] + "..." 
            if len(response_text) > 300 
            else response_text
        )
        result.goal_completed = (
            relevance_score >= QUALITY_PASS_THRESHOLD and has_keywords
        )
        result.is_fallback = any(
            phrase in response_text.lower() 
            for phrase in FALLBACK_PHRASES
        )
        
        return result


class OpenAITester(LLMTester):
    """OpenAI-specific implementation of LLM testing."""
    
    def __init__(self, api_key: str, base_url: str = None, extra_headers: dict = None):
        """Initialize OpenAI tester with API key."""
        super().__init__(Provider.OPENAI)
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)
        self.extra_headers = extra_headers or {}
    
    async def test(self, model: str, test_case: TestCase) -> TestResult:
        """
        Test OpenAI model with streaming.
        
        Args:
            model: OpenAI model identifier
            test_case: Test case to evaluate
            
        Returns:
            TestResult with performance and quality metrics
        """
        self.logger.info(f"Testing {model} on {test_case.id}")
        
        start_time = time.time()
        first_token_time = None
        response_text = ""
        token_count = 0
        
        try:
            # Build kwargs with extra_headers if provided
            create_kwargs = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant analyzing business documents. "
                            "Be concise and accurate."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Document:\n{test_case.document}\n\n"
                            f"Question: {test_case.query}"
                        )
                    }
                ],
                "temperature": DEFAULT_TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "stream": True
            }
            
            # Add extra_headers if provided
            if self.extra_headers:
                create_kwargs["extra_headers"] = self.extra_headers
            
            stream = self.client.chat.completions.create(**create_kwargs)
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    if first_token_time is None:
                        first_token_time = time.time() - start_time
                    
                    response_text += chunk.choices[0].delta.content
                    token_count += 1
            
            return self._create_result(
                model, test_case, start_time, first_token_time,
                response_text, token_count
            )
            
        except Exception as e:
            return self._create_result(
                model, test_case, start_time, None, "", 0, error=e
            )


class AnthropicTester(LLMTester):
    """Anthropic Claude-specific implementation."""
    
    def __init__(self, api_key: str):
        """Initialize Anthropic tester with API key."""
        super().__init__(Provider.ANTHROPIC)
        self.client = anthropic.Anthropic(api_key=api_key)
    
    async def test(self, model: str, test_case: TestCase) -> TestResult:
        """Test Anthropic model with streaming."""
        self.logger.info(f"Testing {model} on {test_case.id}")
        
        start_time = time.time()
        first_token_time = None
        response_text = ""
        token_count = 0
        
        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=MAX_TOKENS,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Document:\n{test_case.document}\n\n"
                        f"Question: {test_case.query}"
                    )
                }]
            ) as stream:
                for text in stream.text_stream:
                    if first_token_time is None:
                        first_token_time = time.time() - start_time
                    
                    response_text += text
                    token_count += 1
            
            return self._create_result(
                model, test_case, start_time, first_token_time,
                response_text, token_count
            )
            
        except Exception as e:
            return self._create_result(
                model, test_case, start_time, None, "", 0, error=e
            )


class GroqTester(LLMTester):
    """Groq-specific implementation for ultra-fast inference."""
    
    def __init__(self, api_key: str):
        """Initialize Groq tester with API key."""
        super().__init__(Provider.GROQ)
        self.client = Groq(api_key=api_key)
    
    async def test(self, model: str, test_case: TestCase) -> TestResult:
        """Test Groq model with streaming."""
        self.logger.info(f"Testing {model} on {test_case.id}")
        
        start_time = time.time()
        first_token_time = None
        response_text = ""
        token_count = 0
        
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant analyzing business documents."
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Document:\n{test_case.document}\n\n"
                            f"Question: {test_case.query}"
                        )
                    }
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    if first_token_time is None:
                        first_token_time = time.time() - start_time
                    
                    response_text += chunk.choices[0].delta.content
                    token_count += 1
            
            return self._create_result(
                model, test_case, start_time, first_token_time,
                response_text, token_count
            )
            
        except Exception as e:
            return self._create_result(
                model, test_case, start_time, None, "", 0, error=e
            )


class BenchmarkSuite:
    """
    Main benchmark orchestration class.
    
    Coordinates testing across multiple providers and aggregates results.
    """
    
    def __init__(self, test_cases: List[TestCase]):
        """
        Initialize benchmark suite.
        
        Args:
            test_cases: List of test cases to run
        """
        self.test_cases = test_cases
        self.results: List[TestResult] = []
        self.logger = logging.getLogger(f"{__name__}.BenchmarkSuite")
    
    def add_result(self, result: TestResult) -> None:
        """Add a test result to the suite."""
        self.results.append(result)
    
    def calculate_aggregates(self) -> List[AggregateMetrics]:
        """
        Calculate aggregate metrics grouped by provider and model.
        
        Returns:
            List of AggregateMetrics sorted by goal completion rate
        """
        if not self.results:
            self.logger.warning("No results to aggregate")
            return []
        
        # Group results by model
        by_model: Dict[str, Dict] = {}
        
        for result in self.results:
            key = f"{result.provider}_{result.model}"
            
            if key not in by_model:
                by_model[key] = {
                    "provider": result.provider,
                    "model": result.model,
                    "total_tests": 0,
                    "successful_tests": 0,
                    "goals_completed": 0,
                    "fallbacks": 0,
                    "first_token_times": [],
                    "latencies": [],
                    "throughputs": [],
                    "relevance_scores": []
                }
            
            stats = by_model[key]
            stats["total_tests"] += 1
            
            if result.success:
                stats["successful_tests"] += 1
                if result.first_token_time:
                    stats["first_token_times"].append(result.first_token_time)
                if result.total_latency:
                    stats["latencies"].append(result.total_latency)
                if result.throughput:
                    stats["throughputs"].append(result.throughput)
                if result.relevance_score:
                    stats["relevance_scores"].append(result.relevance_score)
            
            if result.goal_completed:
                stats["goals_completed"] += 1
            
            if result.is_fallback:
                stats["fallbacks"] += 1
        
        # Calculate averages and create AggregateMetrics objects
        aggregates = []
        for stats in by_model.values():
            total = stats["total_tests"]
            
            aggregates.append(AggregateMetrics(
                provider=stats["provider"],
                model=stats["model"],
                total_tests=total,
                success_rate=round((stats["successful_tests"] / total) * 100, 2),
                goal_completion_rate=round((stats["goals_completed"] / total) * 100, 2),
                fallback_rate=round((stats["fallbacks"] / total) * 100, 2),
                avg_first_token_time=round(
                    sum(stats["first_token_times"]) / len(stats["first_token_times"]), 3
                ) if stats["first_token_times"] else None,
                avg_latency=round(
                    sum(stats["latencies"]) / len(stats["latencies"]), 3
                ) if stats["latencies"] else None,
                avg_throughput=round(
                    sum(stats["throughputs"]) / len(stats["throughputs"]), 2
                ) if stats["throughputs"] else None,
                avg_relevance_score=round(
                    sum(stats["relevance_scores"]) / len(stats["relevance_scores"]), 2
                ) if stats["relevance_scores"] else None
            ))
        
        # Sort by goal completion rate, then by latency
        aggregates.sort(
            key=lambda x: (x.goal_completion_rate, -x.avg_latency if x.avg_latency else 0),
            reverse=True
        )
        
        return aggregates
    
    def save_results(self, output_path: Path = Path("llm_benchmark_results.json")) -> None:
        """
        Save detailed results to JSON file.
        
        Args:
            output_path: Path to output JSON file
        """
        output = {
            "timestamp": datetime.now().isoformat(),
            "test_cases": [asdict(tc) for tc in self.test_cases],
            "aggregate_metrics": [asdict(m) for m in self.calculate_aggregates()],
            "detailed_results": [r.to_dict() for r in self.results]
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        self.logger.info(f"Results saved to {output_path}")
    
    def print_results(self) -> None:
        """Print formatted benchmark results to console."""
        aggregates = self.calculate_aggregates()
        
        if not aggregates:
            print("❌ No results to display")
            return
        
        print("\n" + "="*120)
        print("📊 COMPREHENSIVE LLM BENCHMARK RESULTS")
        print("="*120)
        
        # Table header
        print(f"\n{'Provider':<12} {'Model':<28} {'Success%':<10} {'Goal%':<10} "
              f"{'Fallback%':<12} {'TTFT':<10} {'Latency':<10} {'Tokens/s':<12} {'Quality':<10}")
        print("-"*120)
        
        # Table rows
        for metrics in aggregates:
            print(f"{metrics.provider:<12} {metrics.model:<28} "
                  f"{metrics.success_rate:<10.1f} "
                  f"{metrics.goal_completion_rate:<10.1f} "
                  f"{metrics.fallback_rate:<12.1f} "
                  f"{metrics.avg_first_token_time or 'N/A':<10} "
                  f"{metrics.avg_latency or 'N/A':<10} "
                  f"{metrics.avg_throughput or 'N/A':<12} "
                  f"{metrics.avg_relevance_score or 'N/A':<10}")
        
        # Winner
        best = aggregates[0]
        print("\n" + "="*120)
        print(f"🏆 BEST OVERALL: {best.provider} {best.model}")
        print(f"   Goal Completion: {best.goal_completion_rate}%")
        print(f"   Quality Score: {best.avg_relevance_score}/10")
        print(f"   Latency: {best.avg_latency}s")
        print(f"   Throughput: {best.avg_throughput} tokens/s")
        print("="*120)

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return ""

def create_test_cases() -> List[TestCase]:
    """
    Create test cases from PDF documents with custom questions.
    
    Returns:
        List of TestCase objects
    """
    # Path to your PDF files
    pdf_dir = Path(__file__).parent / "test_documents"
    
    # Extract text from your PDFs once
    research_paper_text = extract_text_from_pdf(pdf_dir / "research_paper.pdf")
    tesla_report_text = extract_text_from_pdf(pdf_dir / "tesla_annual_report_2025.pdf")
    
    # Define your questions here - Add as many as you want!
    test_cases = []
    
    # Research Paper Questions
    research_questions = [
        {
            "query": "What core problem does the paper aim to solve for bipedal robots, and what are its main contributions?",
            "keywords": ["versatile", "dynamic", "robust", "bipedal", "locomotion", "dual-history", "task randomization", "zero-shot"],
            "complexity": "MEDIUM"
        },
        {
            "query": "Describe the dual-history policy architecture and explain how it enables adaptability and sim-to-real robustness.",
            "keywords": ["dual-history", "short I/O", "long I/O", "1D CNN", "MLP", "system identification", "real-time control"],
            "complexity": "COMPLEX"
        },
        {
            "query": "Summarize the three-stage training pipeline and how task and dynamics randomization contribute to generalization.",
            "keywords": ["single-task", "task randomization", "dynamics randomization", "curriculum", "sim-to-real"],
            "complexity": "MEDIUM"
        },
        {
            "query": "What real-world locomotion skills were demonstrated and what quantitative results verify zero-shot transfer?",
            "keywords": ["walking", "running", "jumping", "standing", "400 m", "≈2 min 34 s", "0.47 m apex", "no finetuning"],
            "complexity": "MEDIUM"
        },
        {
            "query": "What limitations do the authors acknowledge, and what future directions do they propose?",
            "keywords": ["no vision", "privileged reward", "limited references", "future", "broader skills", "vision awareness"],
            "complexity": "EASY"
        }
    ]

    
    # Tesla Annual Report Questions
    tesla_questions = [
        {
            "query": "What are Tesla’s key operational and strategic achievements highlighted for fiscal year 2024–2025?",
            "keywords": ["8 million vehicles", "37 GWh energy storage", "Robotaxi launch Austin", "Model Y factories", "Samsung chip deal"],
            "complexity": "EASY"
        },
        {
            "query": "Summarize the vision of Master Plan Part IV and the concept of 'Sustainable Abundance'.",
            "keywords": ["Sustainable Abundance", "AI", "mobility", "energy", "Optimus", "Robotaxi", "democratize autonomous services"],
            "complexity": "MEDIUM"
        },
        {
            "query": "Describe the structure and performance targets of the 2025 CEO Performance Award for Elon Musk.",
            "keywords": ["Adjusted EBITDA", "1 million Robotaxis", "1 million AI Bots", "$7.5 trillion", "vesting 7.5–10 years", "performance milestones"],
            "complexity": "COMPLEX"
        },
        {
            "query": "What corporate-governance and shareholder-engagement reforms are introduced in 2025?",
            "keywords": ["Shareholder Platform", "supermajority elimination", "proxy access", "retail investor participation 65%", "governance updates"],
            "complexity": "MEDIUM"
        },
        {
            "query": "Summarize Tesla’s approach to executive compensation and how it aligns with shareholder interests.",
            "keywords": ["equity-based", "stock options", "no cash bonus", "performance-linked", "say-on-pay", "long-term value creation"],
            "complexity": "MEDIUM"
        }
    ]


    
    # Create test cases for Research Paper
    for idx, q in enumerate(research_questions):
        test_cases.append(TestCase(
            id=f"research_paper_q{idx+1}",
            document=research_paper_text,
            query=q["query"],
            expected_keywords=q["keywords"],
            complexity=q["complexity"]
        ))
    
    # Create test cases for Tesla Report
    for idx, q in enumerate(tesla_questions):
        test_cases.append(TestCase(
            id=f"tesla_report_q{idx+1}",
            document=tesla_report_text,
            query=q["query"],
            expected_keywords=q["keywords"],
            complexity=q["complexity"]
        ))
    
    return test_cases


async def main() -> None:
    """
    Main entry point for benchmark execution.
    
    Loads configuration from environment and runs comprehensive tests.
    """
    # Load environment variables
    load_dotenv()
    
    # Create test suite
    test_cases = create_test_cases()
    suite = BenchmarkSuite(test_cases)
    
    logger.info("="*120)
    logger.info(f"🚀 Starting Comprehensive LLM Benchmark - {len(test_cases)} test cases")
    logger.info("="*120)
    
    # Initialize testers
    testers = []
    
    # if openai_key := os.getenv("OPENAI_API_KEY"):
    #     openai_tester = OpenAITester(openai_key)
    #     testers.extend([
    #         (openai_tester, "gpt-4o-mini"),
    #         (openai_tester, "gpt-4o"),
    #         (openai_tester, "gpt-3.5-turbo"),
    #     ])
    
    # if anthropic_key := os.getenv("ANTHROPIC_API_KEY"):
    #     anthropic_tester = AnthropicTester(anthropic_key)
    #     testers.extend([
    #         (anthropic_tester, "claude-3-5-sonnet-20241022"),
    #         (anthropic_tester, "claude-3-haiku-20240307"),
    #     ])
    
    # if groq_key := os.getenv("GROQ_API_KEY"):
    #     groq_tester = GroqTester(groq_key)
    #     testers.extend([
    #         (groq_tester, "llama-3.1-70b-versatile"),
    #         (groq_tester, "mixtral-8x7b-32768"),
    #     ])
    
    # OpenRouter Models - Each with separate API key
    openrouter_base_url = "https://openrouter.ai/api/v1"
    openrouter_headers = {
        "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:3000"),
        "X-Title": os.getenv("SITE_NAME", "QA-Chatbot Benchmark"),
    }
    
    # Qwen3 235B A22B
    if qwen_key := os.getenv("QWEN3_235B_API_KEY"):
        qwen_tester = OpenAITester(
            api_key=qwen_key,
            base_url=openrouter_base_url,
            extra_headers=openrouter_headers
        )
        testers.append((qwen_tester, "qwen/qwen3-235b-a22b:free"))
    
    # GPT-OSS 20B
    if gpt_oss_key := os.getenv("GPT_OSS_API_KEY"):
        gpt_oss_tester = OpenAITester(
            api_key=gpt_oss_key,
            base_url=openrouter_base_url,
            extra_headers=openrouter_headers
        )
        testers.append((gpt_oss_tester, "openai/gpt-oss-20b:free"))
    
    # Llama 4 Maverick
    if llama_maverick_key := os.getenv("LLAMA_MAVERICK_API_KEY"):
        llama_maverick_tester = OpenAITester(
            api_key=llama_maverick_key,
            base_url=openrouter_base_url,
            extra_headers=openrouter_headers
        )
        testers.append((llama_maverick_tester, "meta-llama/llama-4-maverick:free"))

    if not testers:
        logger.error("No API keys found. Please set environment variables.")
        return
    
    # Run all tests
    for tester, model in testers:
        logger.info(f"\n{'='*120}")
        logger.info(f"Testing {tester.provider.value} - {model}")
        logger.info(f"{'='*120}")
        
        for test_case in test_cases:
            result = await tester.test(model, test_case)
            suite.add_result(result)
            
            if result.success:
                logger.info(
                    f"  ✅ {test_case.id}: TTFT={result.first_token_time}s, "
                    f"Latency={result.total_latency}s, Quality={result.relevance_score}/10"
                )
            else:
                logger.error(f"  ❌ {test_case.id}: {result.error_message}")
    
    # Print and save results
    suite.print_results()
    suite.save_results()
    
    logger.info("\n✅ Benchmark complete!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Benchmark interrupted by user")
    except Exception as e:
        logger.exception(f"❌ Benchmark failed: {e}")
        raise