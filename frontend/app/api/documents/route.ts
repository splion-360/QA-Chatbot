import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@utils/supabase/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080'

export async function GET(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    return NextResponse.json({ message: 'Unauthorized' }, { status: 401 })
  }

  const { searchParams } = new URL(request.url)
  const page = searchParams.get('page') || '1'
  const limit = searchParams.get('limit') || '10'

  try {
    const response = await fetch(
      `${BACKEND_URL}/api/v1/documents/?user_id=${user.id}&page=${page}&limit=${limit}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to fetch documents:', error)
    return NextResponse.json(
      { message: 'Failed to fetch documents' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    return NextResponse.json({ message: 'Unauthorized' }, { status: 401 })
  }

  try {
    const formData = await request.formData()
    const file = formData.get('file') as File
    const title = formData.get('title') as string

    if (!file || !title) {
      return NextResponse.json(
        { message: 'File and title are required' },
        { status: 400 }
      )
    }

    const backendFormData = new FormData()
    backendFormData.append('file', file)
    if (title) {
      backendFormData.append('title', title)
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/documents/upload?user_id=${user.id}`,
      {
        method: 'POST',
        body: backendFormData,
      }
    )

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || `Backend error: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to upload document:', error)
    return NextResponse.json(
      { message: error instanceof Error ? error.message : 'Failed to upload document' },
      { status: 500 }
    )
  }
}