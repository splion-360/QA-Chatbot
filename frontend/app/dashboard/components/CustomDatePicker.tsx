import * as React from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { useForkRef } from '@mui/material/utils';
import Button from '@mui/material/Button';
import CalendarTodayRoundedIcon from '@mui/icons-material/CalendarTodayRounded';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker, DatePickerFieldProps } from '@mui/x-date-pickers/DatePicker';
import {
  useParsedFormat,
  usePickerContext,
  useSplitFieldProps,
} from '@mui/x-date-pickers';

interface ButtonFieldProps extends DatePickerFieldProps {}

function ButtonField(props: ButtonFieldProps) {
  const { forwardedProps } = useSplitFieldProps(props, 'date');
  const pickerContext = usePickerContext();
  const handleRef = useForkRef(pickerContext.triggerRef, pickerContext.rootRef);
  const currentDate = dayjs().format('MMM DD, YYYY');

  // Filter out props that shouldn't be passed to DOM elements
  const { slotProps, inputRef, ...validProps } = forwardedProps;

  return (
    <Button
      {...validProps}
      variant="outlined"
      ref={handleRef}
      size="small"
      startIcon={<CalendarTodayRoundedIcon fontSize="small" />}
      sx={{ minWidth: 'fit-content' }}
      disabled
    >
      {currentDate}
    </Button>
  );
}

export default function CustomDatePicker() {
  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <DatePicker
        value={dayjs()}
        label={dayjs().format('MMM DD, YYYY')}
        onChange={() => {}} // No-op function since editing is disabled
        slots={{ field: ButtonField }}
        disabled
        readOnly
      />
    </LocalizationProvider>
  );
}
