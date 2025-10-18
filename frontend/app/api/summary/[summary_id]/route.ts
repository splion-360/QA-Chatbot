import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/utils/supabase/server';

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ summary_id: string }> }
) {
  try {
    const supabase = await createClient();
    const { summary_id } = await params;
    
    // Authenticate
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Delete summary
    const { error: deleteError } = await supabase
      .from('summary')
      .delete()
      .eq('summary_id', summary_id)
      .eq('user_id', user.id);

    if (deleteError) {
      console.error('Error deleting summary:', deleteError);
      return NextResponse.json(
        { error: 'Failed to delete summary' },
        { status: 500 }
      );
    }

    return NextResponse.json({ 
      success: true,
      message: 'Summary deleted successfully'
    });

  } catch (error) {
    console.error('Unexpected error in DELETE:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
