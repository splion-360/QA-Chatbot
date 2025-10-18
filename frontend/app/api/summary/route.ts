import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/utils/supabase/server';

// POST - Generate new summary
export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient();
    
    // 1. Authenticate user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // 2. Get query parameters
    const { searchParams } = new URL(request.url);
    const start_date = searchParams.get('start_date');
    const end_date = searchParams.get('end_date');

    // 3. Validate inputs
    if (!start_date || !end_date) {
      return NextResponse.json(
        { error: 'Both start_date and end_date are required' },
        { status: 400 }
      );
    }

    const startDate = new Date(start_date);
    const endDate = new Date(end_date);

    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
      return NextResponse.json(
        { error: 'Invalid date format. Use ISO 8601 (e.g., 2024-01-01T00:00:00Z)' },
        { status: 400 }
      );
    }

    if (startDate > endDate) {
      return NextResponse.json(
        { error: 'start_date must be before end_date' },
        { status: 400 }
      );
    }

    // 4. Fetch documents from database
    const { data: documents, error: docsError } = await supabase
      .from('documents')
      .select('document_id, title, content, created_at')
      .eq('user_id', user.id)
      .gte('created_at', start_date)
      .lte('created_at', end_date)
      .order('created_at', { ascending: true });

    if (docsError) {
      console.error('Database error:', docsError);
      return NextResponse.json(
        { error: 'Failed to fetch documents' },
        { status: 500 }
      );
    }

    // 5. Handle no documents case
    if (!documents || documents.length === 0) {
      return NextResponse.json(
        { 
          message: 'No documents found in the specified date range',
          document_count: 0,
          start_date,
          end_date
        },
        { status: 200 }
      );
    }

    // 6. Group chunks by document_id
    const documentMap = new Map<string, {
      title: string;
      content: string[];
      created_at: string;
    }>();

    documents.forEach(doc => {
      if (!documentMap.has(doc.document_id)) {
        documentMap.set(doc.document_id, {
          title: doc.title,
          content: [doc.content],
          created_at: doc.created_at
        });
      } else {
        documentMap.get(doc.document_id)!.content.push(doc.content);
      }
    });

    // 7. Format for summarization
    const aggregatedContent = Array.from(documentMap.entries())
      .map(([id, doc]) => {
        return `## ${doc.title}\n\n${doc.content.join('\n\n')}`;
      })
      .join('\n\n---\n\n');

    // 8. Call Inference Server
    const inferenceUrl = process.env.INFERENCE_SERVER_URL || 'http://localhost:8000';
    
    const summaryResponse = await fetch(`${inferenceUrl}/summarize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content: aggregatedContent,
        start_date,
        end_date,
        document_count: documentMap.size
      }),
    });

    if (!summaryResponse.ok) {
      const errorText = await summaryResponse.text();
      console.error('Inference server error:', errorText);
      return NextResponse.json(
        { error: 'Failed to generate summary from AI service' },
        { status: 500 }
      );
    }

    const { summary: summaryContent } = await summaryResponse.json();

    // 9. Save summary to database
    const { data: savedSummary, error: saveError } = await supabase
      .from('summary')
      .insert({
        user_id: user.id,
        content: summaryContent,
        start_date,
        end_date,
        document_count: documentMap.size
      })
      .select()
      .single();

    if (saveError) {
      console.error('Error saving summary:', saveError);
      return NextResponse.json(
        { error: 'Failed to save summary' },
        { status: 500 }
      );
    }

    // 10. Return success response
    return NextResponse.json({
      success: true,
      summary_id: savedSummary.summary_id,
      summary: summaryContent,
      document_count: documentMap.size,
      start_date,
      end_date,
      created_at: savedSummary.created_at
    });

  } catch (error) {
    console.error('Unexpected error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// GET - Retrieve summaries
export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const summary_id = searchParams.get('summary_id');

    if (summary_id) {
      // Get specific summary
      const { data: summary, error } = await supabase
        .from('summary')
        .select('*')
        .eq('summary_id', summary_id)
        .eq('user_id', user.id)
        .single();

      if (error || !summary) {
        return NextResponse.json(
          { error: 'Summary not found' },
          { status: 404 }
        );
      }

      return NextResponse.json({ summary });
    } else {
      // Get all summaries
      const { data: summaries, error } = await supabase
        .from('summary')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

      if (error) {
        return NextResponse.json(
          { error: 'Failed to fetch summaries' },
          { status: 500 }
        );
      }

      return NextResponse.json({ summaries: summaries || [] });
    }

  } catch (error) {
    console.error('Error in GET summary:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
