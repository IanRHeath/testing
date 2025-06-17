import React, { useState, useEffect, useRef } from 'react';

// --- Helper Components ---

// Icon for the user avatar
const UserIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8 text-white bg-blue-500 rounded-full p-1.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
    </svg>
);

// Icon for the AI agent avatar
const AiIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8 text-white bg-indigo-600 rounded-full p-1.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M19.965 8.521C19.988 8.347 20 8.173 20 8c0-2.76-2.24-5-5-5S10 5.24 10 8c0 .173.012.347.035.521C10.012 8.695 10 8.828 10 9c0 2.76 2.24 5 5 5s5-2.24 5-5c0-.172-.012-.305-.035-.479zM9 14c-2.67 0-8 1.34-8 4v2h9.54c-.45-.83-.7-1.79-.7-2.82 0-.39.04-.78.11-1.16C9.69 14.05 9.35 14 9 14zM15 16c-2.67 0-5.18 1.04-7 2.72.83.63 1.78 1.13 2.82 1.48C12.18 20.58 13.54 21 15 21c2.67 0 8-1.34 8-4v-2c0-2.66-5.33-4-8-4z" />
    </svg>
);

// Component to render a single Jira ticket from the search results
const JiraTicket = ({ ticket }) => (
    <div className="border border-gray-200 rounded-lg p-4 mb-3 bg-gray-50 hover:bg-gray-100 transition-colors duration-200">
        <div className="flex justify-between items-center mb-2">
            <a href={ticket.url} target="_blank" rel="noopener noreferrer" className="text-lg font-semibold text-blue-600 hover:underline">{ticket.key}</a>
            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${ticket.status === 'Open' || ticket.status === 'Opened' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}`}>
                {ticket.status}
            </span>
        </div>
        <p className="text-gray-800 mb-3">{ticket.summary}</p>
        <div className="text-xs text-gray-500 grid grid-cols-2 gap-x-4">
            <p><strong className="font-medium text-gray-600">Assignee:</strong> {ticket.assignee}</p>
            <p><strong className="font-medium text-gray-600">Priority:</strong> {ticket.priority}</p>
            <p><strong className="font-medium text-gray-600">Created:</strong> {ticket.created}</p>
            <p><strong className="font-medium text-gray-600">Updated:</strong> {ticket.updated}</p>
        </div>
    </div>
);

// --- Main App Component ---
export default function App() {
    // State Management
    const [messages, setMessages] = useState([
        { role: 'ai', type: 'text', content: "Welcome to the Jira Triage LLM Agent! How can I help you today?" }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    // Effect to auto-scroll to the latest message
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Function to handle sending a message
    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage = { role: 'user', type: 'text', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        // Prepare the history for the API call
        const apiHistory = messages.map(msg => ({
            role: msg.role,
            // The backend needs the raw text output for history context
            content: msg.raw_output || msg.content 
        }));

        try {
            const response = await fetch('http://127.0.0.1:5001/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: input, history: apiHistory })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.content || 'An API error occurred.');
            }

            const data = await response.json();

            // Add the new AI message to our state
            setMessages(prev => [...prev, { role: 'ai', ...data }]);

        } catch (error) {
            setMessages(prev => [...prev, { role: 'ai', type: 'error', content: error.message }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-100 font-sans">
            <header className="bg-white border-b border-gray-200 p-4 shadow-sm">
                <h1 className="text-xl font-bold text-center text-gray-800">Jira Triage Agent</h1>
            </header>

            <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
                <div className="max-w-3xl mx-auto">
                    {messages.map((msg, index) => (
                        <div key={index} className={`flex items-start gap-4 mb-6 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.role === 'ai' && <AiIcon />}
                            
                            <div className={`rounded-lg p-4 max-w-lg ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-white text-gray-800 shadow-sm border border-gray-100'}`}>
                                {msg.type === 'text' && <p>{msg.content}</p>}
                                {msg.type === 'error' && <p className="text-red-600"><strong className="font-bold">Error:</strong> {msg.content}</p>}
                                {msg.type === 'search_result' && (
                                    <div>
                                        <p className="font-semibold mb-3 text-gray-900">I found the following tickets:</p>
                                        {msg.content.map((ticket, i) => (
                                            <JiraTicket key={i} ticket={ticket} />
                                        ))}
                                    </div>
                                )}
                            </div>

                            {msg.role === 'user' && <UserIcon />}
                        </div>
                    ))}
                    {isLoading && (
                         <div className="flex items-start gap-4 mb-6 justify-start">
                            <AiIcon />
                            <div className="rounded-lg p-4 max-w-lg bg-white text-gray-800 shadow-sm border border-gray-100">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse"></div>
                                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse delay-75"></div>
                                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse delay-150"></div>
                                    <span className="text-gray-500">Thinking...</span>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </main>

            <footer className="bg-white border-t border-gray-200 p-4">
                <div className="max-w-3xl mx-auto">
                    <div className="flex items-center bg-gray-100 rounded-lg p-2">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Type your Jira request..."
                            className="flex-1 bg-transparent border-none focus:ring-0 outline-none px-2 text-gray-800"
                            disabled={isLoading}
                        />
                        <button
                            onClick={handleSend}
                            disabled={isLoading || !input.trim()}
                            className="bg-blue-500 text-white rounded-md px-4 py-2 text-sm font-semibold hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
                        >
                            Send
                        </button>
                    </div>
                </div>
            </footer>
        </div>
    );
}
