'use client';

import Box from '@mui/material/Box';

interface InfinityLoaderProps {
  size?: number;
}

export default function InfinityLoader({ size = 40 }: InfinityLoaderProps) {
  const strokeWidth = size * 0.1;
  const markerSize = size * 0.15;
  
  return (
    <Box
      sx={{
        width: size,
        height: size,
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{
          position: 'absolute',
        }}
      >
        <path
          d={`M ${size * 0.2} ${size * 0.5} 
              C ${size * 0.2} ${size * 0.2}, ${size * 0.4} ${size * 0.2}, ${size * 0.5} ${size * 0.5}
              C ${size * 0.6} ${size * 0.8}, ${size * 0.8} ${size * 0.8}, ${size * 0.8} ${size * 0.5}
              C ${size * 0.8} ${size * 0.2}, ${size * 0.6} ${size * 0.2}, ${size * 0.5} ${size * 0.5}
              C ${size * 0.4} ${size * 0.8}, ${size * 0.2} ${size * 0.8}, ${size * 0.2} ${size * 0.5}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          opacity={0.3}
        />
      </svg>
      
      <Box
        sx={{
          width: markerSize,
          height: markerSize,
          backgroundColor: 'white',
          borderRadius: '50%',
          position: 'absolute',
          boxShadow: '0 0 4px rgba(0,0,0,0.3)',
          animation: 'infinityMove 2s infinite ease-in-out',
          '@keyframes infinityMove': {
            '0%': {
              transform: `translate(${-size * 0.3}px, 0px)`,
            },
            '25%': {
              transform: `translate(0px, ${-size * 0.3}px)`,
            },
            '50%': {
              transform: `translate(${size * 0.3}px, 0px)`,
            },
            '75%': {
              transform: `translate(0px, ${size * 0.3}px)`,
            },
            '100%': {
              transform: `translate(${-size * 0.3}px, 0px)`,
            },
          }
        }}
      />
    </Box>
  );
}