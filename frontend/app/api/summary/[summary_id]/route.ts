import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/utils/supabase/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ summary_id: string }> }
) {
  try {
    const supabase = await createClient();
    const { summary_id } = await params;
    
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Forward to backend
    const backendResponse = await fetch(
      `${BACKEND_URL}/api/v1/summary/${summary_id}/${user.id}`,
      { method: 'DELETE' }
    );
    
    const data = await backendResponse.json();
    return NextResponse.json(data, { status: backendResponse.status });

  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}