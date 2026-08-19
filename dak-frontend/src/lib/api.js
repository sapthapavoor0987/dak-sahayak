import { supabase } from './supabase';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api';

async function getAuthHeader() {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    return { 'Authorization': `Bearer ${session.access_token}` };
  }
  return {};
}

export async function fetchConversations() {
  const authHeader = await getAuthHeader();
  const res = await fetch(`${API_BASE}/conversations`, {
    headers: { ...authHeader, 'Content-Type': 'application/json' }
  });
  if (!res.ok) throw new Error('Failed to fetch conversations');
  const data = await res.json();
  return data.conversations || [];
}

export async function createConversation(title = 'New Chat') {
  const authHeader = await getAuthHeader();
  const res = await fetch(`${API_BASE}/conversations`, {
    method: 'POST',
    headers: { ...authHeader, 'Content-Type': 'application/json' },
    body: JSON.stringify({ title })
  });
  if (!res.ok) throw new Error('Failed to create conversation');
  return await res.json();
}

export async function deleteConversation(conversationId) {
  const authHeader = await getAuthHeader();
  const res = await fetch(`${API_BASE}/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: { ...authHeader }
  });
  if (!res.ok) throw new Error('Failed to delete conversation');
  return await res.json();
}

export async function fetchMessages(conversationId) {
  const authHeader = await getAuthHeader();
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
    headers: { ...authHeader, 'Content-Type': 'application/json' }
  });
  if (!res.ok) throw new Error('Failed to fetch messages');
  const data = await res.json();
  return data.messages || [];
}

export async function sendChatMessageStream({ message, conversationId, language, onChunk, onDone, onError }) {
  const authHeader = await getAuthHeader();
  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { ...authHeader, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        language
      })
    });

    if (!res.ok) {
      throw new Error(`Server returned status ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let accumulated = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      accumulated += chunk;
      if (onChunk) onChunk(chunk, accumulated);
    }

    if (onDone) onDone(accumulated);
  } catch (err) {
    if (onError) onError(err);
  }
}

export async function calculateTariff(payload) {
  const res = await fetch(`${API_BASE}/calculator`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to calculate tariff');
  return await res.json();
}

export async function searchPincode(query) {
  const res = await fetch(`${API_BASE}/pincode/${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Pincode not found');
  return await res.json();
}

export async function reversePincode(lat, lon) {
  const res = await fetch(`${API_BASE}/reverse-pincode?lat=${lat}&lon=${lon}`);
  if (!res.ok) throw new Error('Failed to reverse geocode location');
  return await res.json();
}
