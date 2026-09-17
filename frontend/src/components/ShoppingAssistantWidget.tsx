import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { askAssistant } from "../api/assistant";
import type { AssistantMessage } from "../api/assistant";
import { extractErrorMessage } from "../api/client";

interface DisplayMessage extends AssistantMessage {
  referencedProductIds?: string[];
}

export function ShoppingAssistantWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question || isSending) return;

    setError(null);
    setInput("");
    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setIsSending(true);

    try {
      const response = await askAssistant(question, history);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply, referencedProductIds: response.referenced_product_ids },
      ]);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="assistant-widget">
      {isOpen && (
        <div className="assistant-panel">
          <div className="assistant-panel-header">
            <span>NEXORA Shopping Assistant</span>
            <button type="button" className="link-button" onClick={() => setIsOpen(false)}>
              Close
            </button>
          </div>

          <div className="assistant-messages">
            {messages.length === 0 && (
              <p className="hint">
                Ask about products, e.g. "What laptops do you have under $1000?"
              </p>
            )}
            {messages.map((message, index) => (
              <div key={index} className={`assistant-message ${message.role}`}>
                <p>{message.content}</p>
                {message.referencedProductIds && message.referencedProductIds.length > 0 && (
                  <div className="assistant-references">
                    {message.referencedProductIds.map((id) => (
                      <Link key={id} to={`/products/${id}`} onClick={() => setIsOpen(false)}>
                        View product
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isSending && <p className="hint">Thinking...</p>}
          </div>

          {error && <p className="assistant-error">{error}</p>}

          <form className="assistant-input-row" onSubmit={handleSubmit}>
            <input
              type="text"
              placeholder="Ask NEXORA..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              disabled={isSending}
            />
            <button type="submit" className="button primary" disabled={isSending || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      )}

      <button
        type="button"
        className="assistant-toggle"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label="Open shopping assistant"
      >
        {isOpen ? "Close" : "Ask NEXORA"}
      </button>
    </div>
  );
}
