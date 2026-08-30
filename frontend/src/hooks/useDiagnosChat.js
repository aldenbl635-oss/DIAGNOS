/**
 * useDiagnosChat — custom hook integrating @ai-sdk/react useChat
 * with the DIAGNOS FastAPI patient simulation backend.
 *
 * Architecture:
 *   useChat (Vercel AI SDK) — handles UI state, input, loading, error
 *        ↓ (custom transport)
 *   FastAPI /api/simulation/:id/ask
 *        ↓
 *   Patient Agent → Semantic Retrieval → Offline Responder → Emotion/State
 *
 * DIAGNOS remains in full control of patient logic.
 * @ai-sdk/react handles: message rendering, loading state, input, scrolling,
 *                        error state, and conversation display.
 */

import { useChat } from '@ai-sdk/react';
import { useRef, useCallback } from 'react';
import { api } from '../api/client';

/**
 * Custom ChatTransport that maps useChat protocol to our FastAPI.
 *
 * @ai-sdk/react expects transport.sendMessages() to return an async stream.
 * We implement this by calling our endpoint and returning a ReadableStream
 * that emits one data chunk in the Vercel AI data-stream text protocol.
 *
 * Protocol reference: https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol
 * Text format: `0:"<text>"\n`  (type 0 = text delta)
 */
class DiagnosChatTransport {
    constructor({ sessionId, getToken, onResponse }) {
        this.sessionId = sessionId;
        this.getToken = getToken;       // () => string JWT
        this.onResponse = onResponse;   // (resp) => void — called with raw FastAPI data
    }

    async sendMessages({ messages, abortSignal }) {
        // The last user message
        const lastUserMsg = [...messages].reverse().find(m => m.role === 'user');
        const text = lastUserMsg?.parts?.find(p => p.type === 'text')?.text
            || lastUserMsg?.content
            || '';

        if (!text.trim()) {
            return new ReadableStream({ start(ctrl) { ctrl.close(); } });
        }

        let data;
        try {
            data = await api.askQuestion(this.sessionId, text);
        } catch (error) {
            console.error('[DiagnosChatTransport] Error response:', error);
            throw new Error(`Backend error: ${error.message}`);
        }

        // Surface full payload to frontend
        this.onResponse?.(data);

        const answer = data.answer || data.response || '';

        // Return exactly what modern @ai-sdk/react ChatTransport requires:
        // A stream of UIMessageChunk objects, NOT raw Uint8Array byte streams.
        return new ReadableStream({
            start(controller) {
                const msgId = Date.now().toString();
                // Tell React SDK to start rendering text
                controller.enqueue({ type: 'text-start', id: msgId });
                // Send the actual text (we do it all at once since it's an offline block)
                controller.enqueue({ type: 'text-delta', id: msgId, delta: answer });
                // Tell React SDK this message is complete
                controller.enqueue({ type: 'finish', finishReason: 'stop' });

                controller.close();
            },
        });
    }
}

/**
 * useDiagnosChat
 *
 * @param {object} opts
 * @param {string}   opts.sessionId      Active simulation session ID
 * @param {function} opts.getToken       Returns the JWT token for auth
 * @param {string}   opts.patientName    For display in chat bubbles
 * @param {function} opts.onResponse     Called with the full FastAPI response
 * @param {string}   opts.initialMessage The patient's opening greeting line
 */
export function useDiagnosChat({
    sessionId,
    getToken,
    patientName = 'Patient',
    onResponse,
    initialMessage = '',
}) {
    const onResponseRef = useRef(onResponse);
    onResponseRef.current = onResponse;

    const transport = useRef(
        new DiagnosChatTransport({
            sessionId,
            getToken,
            onResponse: (resp) => onResponseRef.current?.(resp),
        })
    );

    const chat = useChat({
        transport: transport.current,
        onError: (error) => {
            console.error('[useDiagnosChat] Error:', error);
        },
    });

    /**
     * sendQuestion — call this instead of directly using sendMessage.
     * Adds the message as a user turn so the SDK manages state correctly.
     */
    const sendQuestion = useCallback(
        (text) => {
            if (!text?.trim() || chat.status !== 'ready') return;
            chat.sendMessage({ text: text.trim() });
        },
        [chat]
    );

    return {
        // Re-export SDK state
        messages: chat.messages,
        status: chat.status,   // 'ready' | 'submitted' | 'streaming' | 'error'
        error: chat.error,

        // Input management (used if you bind to the SDK's input)
        input: chat.input,
        handleInputChange: chat.handleInputChange,

        // Custom send function
        sendQuestion,
        setMessages: chat.setMessages,

        // Direct SDK access for advanced use
        _chat: chat,
    };
}
