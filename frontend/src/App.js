import React, { useState, useEffect, useRef } from 'react';

const UserIcon = () => (
    <div className="w-8 h-8 text-white bg-blue-500 rounded-full p-1.5 shrink-0">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
        </svg>
    </div>
);

const AiIcon = () => (
    <div className="w-8 h-8 text-white bg-indigo-600 rounded-full p-1.5 shrink-0">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19.965 8.521C19.988 8.347 20 8.173 20 8c0-2.76-2.24-5-5-5S10 5.24 10 8c0 .173.012.347.035.521C10.012 8.695 10 8.828 10 9c0 2.76 2.24 5 5 5s5-2.24 5-5c0-.172-.012-.305-.035-.479zM9 14c-2.67 0-8 1.34-8 4v2h9.54c-.45-.83-.7-1.79-.7-2.82 0-.39.04-.78.11-1.16C9.69 14.05 9.35 14 9 14zM15 16c-2.67 0-5.18 1.04-7 2.72.83.63 1.78 1.13 2.82 1.48C12.18 20.58 13.54 21 15 21c2.67 0 8-1.34 8-4v-2c0-2.66-5.33-4-8-4z" />
        </svg>
    </div>
);

const CopyIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
        <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
    </svg>
);

const CheckIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-500" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
);

const JiraTicket = ({ ticket }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        const textToCopy = `Key: ${ticket.key}\nSummary: ${ticket.summary}\nURL: ${ticket.url}`;
        navigator.clipboard.writeText(textToCopy).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };
    const statusClass = (ticket.status === 'Open' || ticket.status === 'Opened')
        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
        : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    return (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200">
            <div className="flex justify-between items-start mb-2">
                <a href={ticket.url} target="_blank" rel="noopener noreferrer" className="text-lg font-semibold text-blue-600 dark:text-blue-400 hover:underline">{ticket.key}</a>
                <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${statusClass}`}>{ticket.status}</span>
                    <button onClick={handleCopy} title="Copy Details" className="p-1 text-gray-400 dark:text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                        {copied ? <CheckIcon /> : <CopyIcon />}
                    </button>
                </div>
            </div>
            <p className="text-gray-800 dark:text-gray-300 mb-3">{ticket.summary}</p>
            <div className="text-xs text-gray-500 dark:text-gray-400 grid grid-cols-2 gap-x-4">
                <p><strong className="font-medium text-gray-600 dark:text-gray-300">Assignee:</strong> {ticket.assignee}</p>
                <p><strong className="font-medium text-gray-600 dark:text-gray-300">Priority:</strong> {ticket.priority}</p>
                <p><strong className="font-medium text-gray-600 dark:text-gray-300">Created:</strong> {ticket.created}</p>
                <p><strong className="font-medium text-gray-600 dark:text-gray-300">Updated:</strong> {ticket.updated}</p>
            </div>
        </div>
    );
};

const JiraSummary = ({ summary }) => {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        const textToCopy = `Key: ${summary.key}\n\n${summary.body}`;
        navigator.clipboard.writeText(textToCopy).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    return (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-3 bg-gray-50 dark:bg-gray-800">
            <div className="flex justify-between items-start mb-2">
                <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                    {summary.url !== '#' ? (
                         <a href={summary.url} target="_blank" rel="noopener noreferrer" className="hover:underline">{summary.key}</a>
                    ) : (
                        <span>{summary.key}</span>
                    )}
                </div>
                <button onClick={handleCopy} title="Copy Summary" className="p-1 text-gray-400 dark:text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                    {copied ? <CheckIcon /> : <CopyIcon />}
                </button>
            </div>
            <div className="text-gray-800 dark:text-gray-300">
                <MarkdownRenderer text={summary.body} />
            </div>
        </div>
    );
};


const JiraConfirmation = ({ confirmationData }) => {
    const { draft_data, duplicates } = confirmationData;

    return (
        <div>
            <p className="font-semibold mb-3 text-gray-900 dark:text-gray-100">Please review the final ticket information:</p>
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-4 bg-gray-50 dark:bg-gray-800 text-sm">
                {Object.entries(draft_data).map(([key, value]) => {
                    // Don't show internal fields or empty values
                    if (key === 'project' || key === 'problem_details_group' || key === 'silicon_revisions_group' || !value) return null; 
                    const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    return (
                        <div key={key} className="grid grid-cols-3 gap-2 mb-1">
                            <strong className="font-medium text-gray-600 dark:text-gray-300 col-span-1">{formattedKey}:</strong>
                            <span className="text-gray-800 dark:text-gray-200 col-span-2">{String(value)}</span>
                        </div>
                    );
                })}
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
                <p className="font-semibold mb-2 text-gray-900 dark:text-gray-100">Duplicate Check Results:</p>
                {duplicates && duplicates.length > 0 ? (
                    <div>
                        <p className="text-sm text-yellow-700 dark:text-yellow-400 mb-2">Warning: The following potential duplicates were found:</p>
                        <ul className="list-disc list-inside text-sm">
                            {duplicates.map(ticket => (
                                <li key={ticket.key}>
                                    <a href={ticket.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">
                                        {ticket.key}: {ticket.summary}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>
                ) : (
                    <p className="text-sm text-gray-600 dark:text-gray-400 italic">No potential duplicates were found.</p>
                )}
            </div>
        </div>
    );
};

const MarkdownRenderer = ({ text }) => {
    const createMarkup = (markdownText) => {
        if (typeof markdownText !== 'string') return { __html: '' };

        const urlRegex = /(https?:\/\/[^\s]+)/g;

        const html = markdownText
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">$1</a>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^- (.*$)/gm, '<ul class="list-disc list-inside ml-4"><li>$1</li></ul>')
            .replace(/\n/g, '<br />');

        return { __html: html };
    };
    return <div dangerouslySetInnerHTML={createMarkup(text)} />;
};

const OptionsInput = ({ questionData, onOptionSelect }) => {
    const { options, next_field } = questionData;

    if (!options || options.length === 0) {
        return null;
    }

    if (options.length > 5) {
        return (
            <div className="mt-4">
                <select
                    onChange={(e) => { if (e.target.value) onOptionSelect(next_field, e.target.value) }}
                    className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:ring-blue-500 focus:border-blue-500"
                >
                    <option value="">Select an option...</option>
                    {options.map((option, i) => (
                        <option key={i} value={option}>{option}</option>
                    ))}
                </select>
            </div>
        );
    }

    return (
        <div className="mt-4 flex flex-wrap gap-2">
            {options.map((option, i) => (
                <button
                    key={i}
                    onClick={() => onOptionSelect(next_field, option)}
                    className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-sm font-medium py-1.5 px-3 rounded-full hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                >
                    {option}
                </button>
            ))}
        </div>
    );
};

const ThemeToggle = ({ darkMode, setDarkMode }) => {
    const MoonIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
        </svg>
    );

    const SunIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 100 2h1z" clipRule="evenodd" />
        </svg>
    );

    return (
        <button onClick={() => setDarkMode(!darkMode)} className="p-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
            {darkMode ? <SunIcon /> : <MoonIcon />}
        </button>
    );
};

export default function App() {
    const initialMessage = { role: 'ai', type: 'text', content: "Welcome to the Jira Triage LLM Agent! How can I help you today?" };
    const [messages, setMessages] = useState([initialMessage]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const [showSuggestions, setShowSuggestions] = useState(true);
    const [currentQuestion, setCurrentQuestion] = useState(null);
    const [darkMode, setDarkMode] = useState(false);
    const [inputType, setInputType] = useState('text'); 

    const suggestionPrompts = ["Find stale tickets", "Create a new ticket", "Summarize PLAT-12345"];

    useEffect(() => {
        const isDarkMode = localStorage.getItem('darkMode') === 'true';
        setDarkMode(isDarkMode);
    }, []);

    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('darkMode', 'true');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('darkMode', 'false');
        }
    }, [darkMode]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async (prompt, isAutoTriggered = false) => {
        const textToSend = (typeof prompt === 'string') ? prompt : input;
        
        if (!textToSend.trim() || isLoading) return;

        setInputType('text');
        setShowSuggestions(false);
        if (!isAutoTriggered) {
             const userMessage = { role: 'user', type: 'text', content: textToSend };
             setMessages(prev => [...prev, userMessage]);
        }
       
        setInput('');
        setIsLoading(true);
        setCurrentQuestion(null);

        const apiHistory = messages.map(msg => ({
            role: msg.role,
            content: msg.raw_output || msg.content 
        }));

        try {
            const response = await fetch('http://127.0.0.1:5001/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: textToSend, history: apiHistory })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.content || 'An API error occurred.');
            
            const nextField = data.content?.next_field;
            if (nextField === 'description' || nextField === 'steps_to_reproduce') {
                setInputType('textarea');
            } else {
                setInputType('text'); 
            }

            if (data.type === 'options_request') {
                const questionMessage = { role: 'ai', type: 'text', content: data.content.question, raw_output: data.raw_output };
                setMessages(prev => [...prev, questionMessage]);
                setCurrentQuestion(data.content);
            } else {
                setMessages(prev => [...prev, { role: 'ai', ...data }]);
            }
        } catch (error) {
            setMessages(prev => [...prev, { role: 'ai', type: 'error', content: error.message }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleOptionSelect = (fieldName, fieldValue) => {
        setInputType('text'); 
        const userMessage = { role: 'user', type: 'text', content: fieldValue };
        setMessages(prev => [...prev, userMessage]);
        
        const command = `set_ticket_field(field_name='${fieldName}', field_value='${fieldValue}')`;
        handleSend(command, true);
    };

    const handleConfirmCreation = () => {
        const command = `finalize_ticket_creation(confirmed=True)`;
        const userMessage = { role: 'user', type: 'text', content: "Yes, create the ticket." };
        setMessages(prev => [...prev, userMessage]);
        handleSend(command, true);
    };

    const handleCancelCreation = () => {
        const command = `cancel_ticket_creation()`;
        const userMessage = { role: 'user', type: 'text', content: "No, cancel it." };
        setMessages(prev => [...prev, userMessage]);
        handleSend(command, true);
    };
    
    const startNewChat = () => {
        setMessages([initialMessage]);
        setShowSuggestions(true);
        setCurrentQuestion(null);
        setInputType('text');
    };

    return (
        <div className="flex flex-col h-screen bg-gray-100 dark:bg-gray-900 font-sans">
            <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 shadow-sm flex justify-between items-center">
                <button onClick={startNewChat} title="Start a new chat" className="text-sm text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 font-semibold py-1 px-3 border border-gray-300 dark:border-gray-600 rounded-md hover:border-blue-500 dark:hover:border-blue-400 transition-colors">
                    New Chat
                </button>
                <h1 className="text-xl font-bold text-center text-gray-800 dark:text-gray-100">Jira Triage Agent</h1>
                <ThemeToggle darkMode={darkMode} setDarkMode={setDarkMode} />
            </header>

            <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
                <div className="max-w-3xl mx-auto">
                    {messages.map((msg, index) => (
                        <div key={index} className={`flex items-start gap-4 mb-6 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.role === 'ai' && <AiIcon />}
                            <div className={`rounded-lg p-4 max-w-lg ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 shadow-sm border border-gray-100 dark:border-gray-700'}`}>
                                {msg.type === 'text' ? (
                                    <MarkdownRenderer text={msg.content} />
                                ) : msg.type === 'error' ? (
                                    <div className="text-red-700 bg-red-100 dark:bg-red-900 dark:text-red-200 p-3 rounded-md"><strong className="font-bold block mb-1">Error:</strong> <MarkdownRenderer text={msg.content} /></div>
                                ) : msg.type === 'search_result' ? (
                                    <div>
                                        <p className="font-semibold mb-3 text-gray-900 dark:text-gray-100">I found the following tickets:</p>
                                        {msg.content.map((ticket, i) => <JiraTicket key={i} ticket={ticket} />)}
                                    </div>
                                ) : msg.type === 'summary_result' ? (
                                    <div>
                                        <p className="font-semibold mb-3 text-gray-900 dark:text-gray-100">Here is the requested summary:</p>
                                        {msg.content.map((summary, i) => <JiraSummary key={i} summary={summary} />)}
                                    </div>
                                ) : msg.type === 'confirmation_request' ? (
                                    <JiraConfirmation confirmationData={msg.content} />
                                ) : null}
                            </div>
                            {msg.role === 'user' && <UserIcon />}
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex items-start gap-4 mb-6 justify-start">
                            <AiIcon />
                            <div className="rounded-lg p-4 max-w-lg bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 shadow-sm border border-gray-100 dark:border-gray-700"><div className="flex items-center gap-2"><div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse"></div><div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse [animation-delay:0.1s]"></div><div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse [animation-delay:0.2s]"></div><span className="text-gray-500 dark:text-gray-400">Thinking...</span></div></div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </main>

            <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4">
                <div className="max-w-3xl mx-auto">
                    {currentQuestion && <OptionsInput questionData={currentQuestion} onOptionSelect={handleOptionSelect} />}

                    {showSuggestions && !currentQuestion && (
                        <div className="flex flex-wrap gap-2 mb-3 justify-center">
                            {suggestionPrompts.map((prompt, i) => (
                                <button key={i} onClick={() => handleSend(prompt)} className="bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm py-1.5 px-3 rounded-full hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors">
                                    {prompt}
                                </button>
                            ))}
                        </div>
                    )}
                    <div className="flex items-start bg-gray-100 dark:bg-gray-900 rounded-lg p-2">
                        {inputType === 'textarea' ? (
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Enter details... Use Enter for new lines. Click Send to submit."
                                className="flex-1 bg-transparent border-none focus:ring-0 outline-none px-2 text-gray-800 dark:text-gray-200 resize-none"
                                rows="4"
                                disabled={isLoading}
                            />
                        ) : (
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => { if (e.key === 'Enter') handleSend() }}
                                placeholder={currentQuestion ? "Please make a selection above or type your answer..." : "Type your Jira request..."}
                                className="flex-1 bg-transparent border-none focus:ring-0 outline-none px-2 text-gray-800 dark:text-gray-200"
                                disabled={isLoading}
                            />
                        )}
                        <button onClick={() => handleSend()} disabled={isLoading || !input.trim()} className="self-end bg-blue-500 text-white rounded-md px-4 py-2 text-sm font-semibold hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors">
                            Send
                        </button>
                    </div>
                </div>
            </footer>
        </div>
    );
}
