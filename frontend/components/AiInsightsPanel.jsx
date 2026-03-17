"use client";

import { useEffect, useState, useRef } from "react";
import { Sparkles, Send, RefreshCcw, AlertCircle, Bot, MessageSquare } from "lucide-react";

export default function AiInsightsPanel({ compact = false }) {
  const [autoInsight, setAutoInsight] = useState("");
  const [autoLoading, setAutoLoading] = useState(false);
  const [autoError, setAutoError] = useState(null);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [questionLoading, setQuestionLoading] = useState(false);
  const [questionError, setQuestionError] = useState(null);
  
  const answerRef = useRef(null);

  const fetchAiInsights = async ({ forQuestion } = { forQuestion: false }) => {
    const payload = {};
    if (forQuestion && question.trim()) payload.question = question.trim();

    try {
      forQuestion ? setQuestionLoading(true) : setAutoLoading(true);
      if (forQuestion) setQuestionError(null); else setAutoError(null);

      const res = await fetch("http://localhost:5000/api/ai-insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (data.status !== "success") {
        throw new Error(data.message || "Insight unavailable");
      }

      if (forQuestion) {
        setAnswer(data.answer || "");
        // Scroll to answer after a short delay to allow render
        setTimeout(() => answerRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
      } else {
        setAutoInsight(data.answer || "");
      }
    } catch (err) {
      const msg = err.message || "Connection error";
      forQuestion ? setQuestionError(msg) : setAutoError(msg);
    } finally {
      forQuestion ? setQuestionLoading(false) : setAutoLoading(false);
    }
  };

  useEffect(() => {
    fetchAiInsights({ forQuestion: false });
    const interval = setInterval(() => fetchAiInsights({ forQuestion: false }), 15000);
    return () => clearInterval(interval);
  }, []);

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim() || questionLoading) return;
    await fetchAiInsights({ forQuestion: true });
  };

  return (
    <div
      className={`bg-[#1f1f1f] rounded-2xl border border-[#2a2a2a] flex flex-col overflow-hidden ${
        compact ? "h-[496px]" : "h-[500px]"
      }`}
    >
      {/* Header */}
      <div className="p-4 border-b border-[#2a2a2a] bg-[#1b1b1b] flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="bg-[#f7c576] p-1.5 rounded-lg">
            <Sparkles size={16} className="text-[#141414]" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-[#f7c576] leading-none">
              AI Ops Insights Agent
            </h2>
            <p className="text-[10px] text-[#f7c576]/60 mt-1 uppercase tracking-wider font-semibold">
              Real-time Analysis
            </p>
          </div>
        </div>
        {autoLoading && (
          <RefreshCcw
            size={14}
            className="text-[#f7c576] animate-spin"
          />
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        
        {/* Automated Insight Bubble */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-[#f7c576]/70">
            <Bot size={14} />
            <span className="text-[11px] font-bold uppercase">
              Automated Briefing
            </span>
          </div>
          
          <div
            className={`p-4 rounded-2xl border ${
              autoError
                ? "bg-red-900/40 border-red-500/60"
                : "bg-[#232323] border-[#353535]"
            }`}
          >
            {autoError ? (
              <div className="flex gap-2 text-red-200 items-start">
                <AlertCircle size={16} className="mt-0.5" />
                <p className="text-xs">{autoError}</p>
              </div>
            ) : (
              <p className="text-sm text-[#f7c576]/80 leading-relaxed whitespace-pre-line">
                {autoInsight || "Analyzing current traffic patterns..."}
              </p>
            )}
          </div>
        </div>

        {/* User Q&A Section */}
        {answer && (
          <div ref={answerRef} className="space-y-2 animate-in fade-in slide-in-from-bottom-2">
            <div className="flex items-center gap-1.5 text-slate-500">
              <MessageSquare size={14} />
              <span className="text-[11px] font-bold uppercase">Response</span>
            </div>
            <div className="p-4 rounded-2xl bg-slate-800 text-slate-100 shadow-inner">
              <p className="text-sm leading-relaxed whitespace-pre-line">{answer}</p>
            </div>
          </div>
        )}
      </div>

      {/* Input Footer */}
      <div className="p-4 bg-[#1b1b1b] border-t border-[#2a2a2a]">
        <form onSubmit={handleAsk} className="relative group">
          <textarea
            className="w-full rounded-xl border border-[#3a3a3a] bg-[#141414] pl-4 pr-12 py-3 text-sm text-[#f7c576] placeholder:text-[#f7c576]/40 focus:outline-none focus:ring-2 focus:ring-[#f7c576]/30 focus:border-[#f7c576] transition-all resize-none"
            rows={2}
            placeholder="Ask about delays, gates, or patterns..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleAsk(e);
                }
            }}
          />
          <button
            type="submit"
            disabled={questionLoading || !question.trim()}
            className="absolute right-2 bottom-2 p-2 bg-[#f7c576] text-[#141414] rounded-lg hover:bg-[#ffd28a] disabled:opacity-30 transition-colors shadow-sm"
          >
            {questionLoading ? (
              <RefreshCcw size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
        </form>
        {questionError && (
          <p className="text-[11px] text-red-300 mt-2 flex items-center gap-1">
            <AlertCircle size={12} /> {questionError}
          </p>
        )}
      </div>
    </div>
  );
}



