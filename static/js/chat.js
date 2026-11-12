/**
 * NovaAI - Chat Engine & Message Renderer
 * Handles Markdown formatting, Syntax Highlighting, Copying, and Feedback.
 */

class ChatEngine {
    constructor() {
        this.viewport = document.getElementById('chat-viewport');
        this.messagesContainer = document.getElementById('messages-container');
        this.welcomeScreen = document.getElementById('welcome-screen');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.scrollBottomBtn = document.getElementById('scroll-bottom-btn');
        this.activeConversationId = null;
        this.isGenerating = false;
        this.onStateChange = null;

        this.configureMarked();
        this.initScrollListener();
    }

    /**
     * Configure Marked.js options
     */
    configureMarked() {
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                breaks: true,
                gfm: true,
                headerIds: false,
                mangle: false
            });
        }
    }

    /**
     * Initialize Scroll to Bottom Button behavior
     */
    initScrollListener() {
        if (!this.viewport || !this.scrollBottomBtn) return;

        this.viewport.addEventListener('scroll', () => {
            const distanceFromBottom = this.viewport.scrollHeight - this.viewport.scrollTop - this.viewport.clientHeight;
            if (distanceFromBottom > 150) {
                this.scrollBottomBtn.classList.remove('hidden');
            } else {
                this.scrollBottomBtn.classList.add('hidden');
            }
        });

        this.scrollBottomBtn.addEventListener('click', () => {
            this.scrollToBottom(true);
        });
    }

    /**
     * Scroll smoothly to the bottom of the viewport
     */
    scrollToBottom(smooth = false) {
        if (!this.viewport) return;
        this.viewport.scrollTo({
            top: this.viewport.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }

    /**
     * Show / Hide Welcome Screen
     */
    setWelcomeVisible(visible) {
        if (this.welcomeScreen) {
            if (visible) {
                this.welcomeScreen.classList.remove('hidden');
            } else {
                this.welcomeScreen.classList.add('hidden');
            }
        }
    }

    /**
     * Clear all current messages in the view
     */
    clearMessages() {
        if (this.messagesContainer) {
            this.messagesContainer.innerHTML = '';
        }
    }

    /**
     * Show / Hide typing indicator
     */
    setTyping(isTyping) {
        if (!this.typingIndicator) return;
        if (isTyping) {
            this.typingIndicator.classList.remove('hidden');
            this.scrollToBottom(true);
        } else {
            this.typingIndicator.classList.add('hidden');
        }
    }

    /**
     * Format Markdown content safely and wrap code blocks with headers and copy buttons
     */
    renderMarkdown(rawContent) {
        if (typeof marked === 'undefined') {
            return rawContent.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        const rawHtml = marked.parse(rawContent);
        const cleanHtml = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = cleanHtml;

        // Enhance <pre><code> blocks
        const preElements = tempDiv.querySelectorAll('pre');
        preElements.forEach(pre => {
            const codeEl = pre.querySelector('code');
            const codeText = codeEl ? codeEl.textContent : pre.textContent;

            // Extract language class if present
            let lang = 'code';
            if (codeEl) {
                const langClass = Array.from(codeEl.classList).find(c => c.startsWith('language-'));
                if (langClass) {
                    lang = langClass.replace('language-', '');
                }
            }

            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-wrapper';

            const header = document.createElement('div');
            header.className = 'code-header';
            header.innerHTML = `
                <span class="code-lang">${lang}</span>
                <button type="button" class="copy-code-btn" title="Copy to clipboard">
                    <i class="fa-regular fa-clipboard"></i>
                    <span>Copy code</span>
                </button>
            `;

            // Attach copy action to code header button
            const copyBtn = header.querySelector('.copy-code-btn');
            copyBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                navigator.clipboard.writeText(codeText).then(() => {
                    copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> <span>Copied!</span>';
                    copyBtn.style.color = 'var(--primary-accent)';
                    setTimeout(() => {
                        copyBtn.innerHTML = '<i class="fa-regular fa-clipboard"></i> <span>Copy code</span>';
                        copyBtn.style.color = '';
                    }, 2000);
                });
            });

            wrapper.appendChild(header);
            const clonePre = pre.cloneNode(true);
            wrapper.appendChild(clonePre);

            pre.replaceWith(wrapper);
        });

        return tempDiv.innerHTML;
    }

    /**
     * Append a user message row to the chat viewport
     */
    appendUserMessage(content, timeStr = null) {
        this.setWelcomeVisible(false);

        const time = timeStr || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const userInitials = (window.CURRENT_USER && window.CURRENT_USER.name)
            ? window.CURRENT_USER.name.substring(0, 2).toUpperCase()
            : 'U';

        const row = document.createElement('div');
        row.className = 'message-row user-row animate-fade-in';
        row.innerHTML = `
            <div class="message-bubble">
                <div class="user-text">${this.escapeHtml(content)}</div>
                <div class="msg-timestamp" style="text-align: right; margin-top: 4px;">${time}</div>
            </div>
            <div class="user-avatar-circle-sm" title="${window.CURRENT_USER?.name || 'User'}">
                <span>${userInitials}</span>
            </div>
        `;

        this.messagesContainer.appendChild(row);
        this.scrollToBottom(true);
        return row;
    }

    /**
     * Create an empty bot message row for live streaming
     */
    createEmptyBotMessage() {
        this.setWelcomeVisible(false);
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const row = document.createElement('div');
        row.className = 'message-row bot-row animate-fade-in';
        row.innerHTML = `
            <div class="bot-avatar-circle">
                <i class="fa-solid fa-sparkles"></i>
            </div>
            <div class="message-bubble">
                <div class="bot-content"></div>
                <div class="message-actions-bar">
                    <button class="msg-action-btn copy-msg-btn" title="Copy response">
                        <i class="fa-regular fa-copy"></i>
                        <span>Copy</span>
                    </button>
                    <button class="msg-action-btn regenerate-btn" title="Regenerate response">
                        <i class="fa-solid fa-rotate-right"></i>
                        <span>Regenerate</span>
                    </button>
                    <button class="msg-action-btn thumbs-up-btn" title="Good response">
                        <i class="fa-regular fa-thumbs-up"></i>
                    </button>
                    <button class="msg-action-btn thumbs-down-btn" title="Bad response">
                        <i class="fa-regular fa-thumbs-down"></i>
                    </button>
                    <span class="msg-timestamp">${time}</span>
                </div>
            </div>
        `;
        this.messagesContainer.appendChild(row);
        this.scrollToBottom();
        return row;
    }

    /**
     * Append an assistant bot message row to the chat viewport
     */
    appendBotMessage(content, messageId = null, rating = null, timeStr = null, animateTyping = false) {
        this.setWelcomeVisible(false);

        const time = timeStr || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const row = document.createElement('div');
        row.className = 'message-row bot-row animate-fade-in';
        if (messageId) {
            row.setAttribute('data-message-id', messageId);
        }

        row.innerHTML = `
            <div class="bot-avatar-circle">
                <i class="fa-solid fa-sparkles"></i>
            </div>
            <div class="message-bubble">
                <div class="bot-content"></div>
                <div class="message-actions-bar">
                    <button class="msg-action-btn copy-msg-btn" title="Copy response">
                        <i class="fa-regular fa-copy"></i>
                        <span>Copy</span>
                    </button>
                    <button class="msg-action-btn regenerate-btn" title="Regenerate response">
                        <i class="fa-solid fa-rotate-right"></i>
                        <span>Regenerate</span>
                    </button>
                    <button class="msg-action-btn thumbs-up-btn ${rating === 'up' ? 'active' : ''}" title="Good response">
                        <i class="fa-regular fa-thumbs-up"></i>
                    </button>
                    <button class="msg-action-btn thumbs-down-btn ${rating === 'down' ? 'active-down' : ''}" title="Bad response">
                        <i class="fa-regular fa-thumbs-down"></i>
                    </button>
                    <span class="msg-timestamp">${time}</span>
                </div>
            </div>
        `;

        const botContentEl = row.querySelector('.bot-content');
        this.messagesContainer.appendChild(row);

        // Bind Action Buttons
        this.bindBotActions(row, content, messageId);

        if (animateTyping) {
            this.streamTyping(botContentEl, content);
        } else {
            botContentEl.innerHTML = this.renderMarkdown(content);
            this.applyPrism(botContentEl);
            this.scrollToBottom();
        }

        return row;
    }

    /**
     * Stop ongoing generation
     */
    stopGeneration() {
        this.isGenerating = false;
        if (this.onStateChange) this.onStateChange(false);
    }

    /**
     * Simulate streaming typing effect
     */
    streamTyping(container, fullText) {
        if (this.onStateChange) this.onStateChange(true);
        const words = fullText.split(/(\s+)/);
        let currentIndex = 0;
        let accumulated = '';
        this.isGenerating = true;

        const interval = setInterval(() => {
            if (currentIndex >= words.length || !this.isGenerating) {
                clearInterval(interval);
                const wasStopped = !this.isGenerating && currentIndex < words.length;
                this.isGenerating = false;
                container.innerHTML = this.renderMarkdown(wasStopped ? accumulated : fullText);
                this.applyPrism(container);
                this.scrollToBottom(true);
                if (this.onStateChange) this.onStateChange(false);
                return;
            }

            accumulated += words[currentIndex];
            currentIndex++;
            container.innerHTML = this.renderMarkdown(accumulated);
            this.scrollToBottom();
        }, 12);
    }

    /**
     * Apply Prism.js Syntax Highlighting to code blocks inside container
     */
    applyPrism(container) {
        if (typeof Prism !== 'undefined') {
            container.querySelectorAll('pre code').forEach(block => {
                Prism.highlightElement(block);
            });
        }
    }

    /**
     * Bind actions: Copy, Regenerate, Thumbs Up, Thumbs Down
     */
    bindBotActions(row, rawContent, messageId) {
        const copyBtn = row.querySelector('.copy-msg-btn');
        const regenBtn = row.querySelector('.regenerate-btn');
        const thumbsUp = row.querySelector('.thumbs-up-btn');
        const thumbsDown = row.querySelector('.thumbs-down-btn');

        // Copy Message
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(rawContent).then(() => {
                    const originalHtml = copyBtn.innerHTML;
                    copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> <span>Copied!</span>';
                    copyBtn.style.color = 'var(--primary-accent)';
                    setTimeout(() => {
                        copyBtn.innerHTML = originalHtml;
                        copyBtn.style.color = '';
                    }, 2000);
                });
            });
        }

        // Regenerate Message
        if (regenBtn) {
            regenBtn.addEventListener('click', () => {
                if (window.NovaApp && typeof window.NovaApp.regenerateLastResponse === 'function') {
                    window.NovaApp.regenerateLastResponse();
                }
            });
        }

        // Thumbs Up / Down Feedback
        if (thumbsUp && messageId) {
            thumbsUp.addEventListener('click', () => {
                this.handleFeedback(messageId, 'up', thumbsUp, thumbsDown);
            });
        }
        if (thumbsDown && messageId) {
            thumbsDown.addEventListener('click', () => {
                this.handleFeedback(messageId, 'down', thumbsUp, thumbsDown);
            });
        }
    }

    /**
     * Handle Thumbs feedback API call and state toggle
     */
    async handleFeedback(messageId, ratingType, upBtn, downBtn) {
        const isAlreadyActive = (ratingType === 'up' && upBtn.classList.contains('active')) ||
                                (ratingType === 'down' && downBtn.classList.contains('active-down'));
        const newRating = isAlreadyActive ? null : ratingType;

        try {
            const res = await fetch(`/api/messages/${messageId}/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rating: newRating })
            });
            const data = await res.json();
            if (data.success) {
                if (newRating === 'up') {
                    upBtn.classList.add('active');
                    downBtn.classList.remove('active-down');
                } else if (newRating === 'down') {
                    downBtn.classList.add('active-down');
                    upBtn.classList.remove('active');
                } else {
                    upBtn.classList.remove('active');
                    downBtn.classList.remove('active-down');
                }
            }
        } catch (err) {
            console.error('Feedback error:', err);
        }
    }

    /**
     * Helper to escape HTML safely
     */
    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

