import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/utils/supabase/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient();
    
    // Authentication only
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const start_date = searchParams.get('start_date');
    const end_date = searchParams.get('end_date');

    // Basic validation
    if (!start_date || !end_date) {
      return NextResponse.json(
        { error: 'Both start_date and end_date are required' },
        { status: 400 }
      );
    }

    // Forward to backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/v1/summary/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: user.id,
        start_date,
        end_date
      }),
    });

    const data = await backendResponse.json();
    return NextResponse.json(data, { status: backendResponse.status });

  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Forward to backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/v1/summary/list/${user.id}`);
    const data = await backendResponse.json();
    
    return NextResponse.json(data, { status: backendResponse.status });

  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}