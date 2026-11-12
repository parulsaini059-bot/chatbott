/**
 * NovaAI - Main Application Controller
 * Handles conversation state, sidebar history, live search, and messaging workflows.
 */

document.addEventListener('DOMContentLoaded', () => {
    class NovaChatApp {
        constructor() {
            this.engine = new ChatEngine();
            this.activeConversationId = null;
            this.conversations = [];
            this.deleteTargetId = null;

            this.cacheDOM();
            this.bindEvents();
            this.loadInitialConversations();
        }

        cacheDOM() {
            // Sidebar elements
            this.sidebar = document.getElementById('sidebar');
            this.sidebarBackdrop = document.getElementById('sidebar-backdrop');
            this.sidebarCollapseBtn = document.getElementById('sidebar-collapse-btn');
            this.mobileSidebarToggle = document.getElementById('mobile-sidebar-toggle');
            this.newChatBtn = document.getElementById('new-chat-btn');
            this.navNewChatBtn = document.getElementById('nav-new-chat-btn');
            this.searchInput = document.getElementById('chat-search-input');
            this.searchClearBtn = document.getElementById('search-clear-btn');
            this.historyContainer = document.getElementById('sidebar-history');
            this.historySkeleton = document.getElementById('history-skeleton');
            this.historyEmpty = document.getElementById('history-empty');

            // Groups
            this.groupToday = document.getElementById('group-today');
            this.listToday = document.getElementById('list-today');
            this.groupYesterday = document.getElementById('group-yesterday');
            this.listYesterday = document.getElementById('list-yesterday');
            this.groupPrev7 = document.getElementById('group-prev-7');
            this.listPrev7 = document.getElementById('list-prev-7');
            this.groupOlder = document.getElementById('group-older');
            this.listOlder = document.getElementById('list-older');

            // User dropdown
            this.userProfileTrigger = document.getElementById('user-profile-trigger');
            this.userDropdownMenu = document.getElementById('user-dropdown-menu');

            // Chat input elements
            this.chatForm = document.getElementById('chat-form');
            this.messageInput = document.getElementById('message-input');
            this.sendBtn = document.getElementById('send-btn');
            this.exportChatBtn = document.getElementById('export-chat-btn');

            // Modal elements
            this.deleteModal = document.getElementById('delete-modal');
            this.modalCancelBtn = document.getElementById('modal-cancel-btn');
            this.modalConfirmDeleteBtn = document.getElementById('modal-confirm-delete-btn');

            // Prompt cards
            this.promptCards = document.querySelectorAll('.prompt-card');
        }

        bindEvents() {
            // Sidebar toggles
            if (this.sidebarCollapseBtn) {
                this.sidebarCollapseBtn.addEventListener('click', () => this.toggleDesktopSidebar());
            }
            if (this.mobileSidebarToggle) {
                this.mobileSidebarToggle.addEventListener('click', () => this.openMobileSidebar());
            }
            if (this.sidebarBackdrop) {
                this.sidebarBackdrop.addEventListener('click', () => this.closeMobileSidebar());
            }

            // New Chat triggers
            if (this.newChatBtn) {
                this.newChatBtn.addEventListener('click', () => this.startNewChat());
            }
            if (this.navNewChatBtn) {
                this.navNewChatBtn.addEventListener('click', () => this.startNewChat());
            }

            // Engine Generation State Listener (Stop button toggle)
            this.engine.onStateChange = (isGenerating) => {
                if (isGenerating) {
                    this.sendBtn.innerHTML = '<i class="fa-solid fa-square" style="font-size: 0.8rem;"></i>';
                    this.sendBtn.disabled = false;
                    this.sendBtn.title = "Stop generating";
                } else {
                    this.sendBtn.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
                    this.sendBtn.title = "Send message";
                    this.handleInputResize();
                }
            };

            // Export Chat Trigger
            if (this.exportChatBtn) {
                this.exportChatBtn.addEventListener('click', () => this.exportCurrentChat());
            }

            // Keyboard shortcut: Ctrl + N for New Chat
            document.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'n') {
                    e.preventDefault();
                    this.startNewChat();
                }
                if (e.key === 'Escape') {
                    this.closeModals();
                }
            });

            // Search listeners
            if (this.searchInput) {
                this.searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
            }
            if (this.searchClearBtn) {
                this.searchClearBtn.addEventListener('click', () => {
                    this.searchInput.value = '';
                    this.searchClearBtn.classList.add('hidden');
                    this.renderConversations(this.conversations);
                });
            }

            // User Profile Dropdown
            if (this.userProfileTrigger && this.userDropdownMenu) {
                this.userProfileTrigger.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.userDropdownMenu.classList.toggle('hidden');
                });
                document.addEventListener('click', () => {
                    if (!this.userDropdownMenu.classList.contains('hidden')) {
                        this.userDropdownMenu.classList.add('hidden');
                    }
                });
            }

            // Chat input handlers
            if (this.messageInput) {
                this.messageInput.addEventListener('input', () => this.handleInputResize());
                this.messageInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (!this.sendBtn.disabled) {
                            this.chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
                        }
                    }
                });
            }

            if (this.chatForm) {
                this.chatForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
            }

            // Delete Modal handlers
            if (this.modalCancelBtn) {
                this.modalCancelBtn.addEventListener('click', () => this.closeDeleteModal());
            }
            if (this.modalConfirmDeleteBtn) {
                this.modalConfirmDeleteBtn.addEventListener('click', () => this.executeDeleteConversation());
            }

            // Prompt Cards click handler
            this.promptCards.forEach(card => {
                card.addEventListener('click', () => {
                    const prompt = card.getAttribute('data-prompt');
                    if (prompt && this.messageInput) {
                        this.messageInput.value = prompt;
                        this.handleInputResize();
                        this.messageInput.focus();
                        this.chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
                    }
                });
            });
        }

        // ---------------------------------------------------------------------
        // Layout & Sidebar Actions
        // ---------------------------------------------------------------------
        toggleDesktopSidebar() {
            this.sidebar.classList.toggle('collapsed');
        }

        openMobileSidebar() {
            this.sidebar.classList.add('mobile-open');
            this.sidebarBackdrop.classList.add('active');
        }

        closeMobileSidebar() {
            this.sidebar.classList.remove('mobile-open');
            this.sidebarBackdrop.classList.remove('active');
        }

        closeModals() {
            if (this.deleteModal) this.deleteModal.classList.add('hidden');
            if (this.userDropdownMenu) this.userDropdownMenu.classList.add('hidden');
            this.closeMobileSidebar();
        }

        handleInputResize() {
            const textarea = this.messageInput;
            textarea.style.height = 'auto';
            const newHeight = Math.min(textarea.scrollHeight, 200);
            textarea.style.height = `${newHeight}px`;

            // Enable or disable send button based on trimmed content
            const hasText = textarea.value.trim().length > 0;
            this.sendBtn.disabled = !hasText || this.engine.isGenerating;
        }

        // ---------------------------------------------------------------------
        // Conversation History Operations
        // ---------------------------------------------------------------------
        async loadInitialConversations() {
            try {
                const res = await fetch('/api/conversations');
                const data = await res.json();
                if (data.success) {
                    this.conversations = data.conversations || [];
                    this.renderGroupedConversations(data.grouped || {});
                }
            } catch (err) {
                console.error('Failed to load conversations:', err);
            } finally {
                if (this.historySkeleton) {
                    this.historySkeleton.classList.add('hidden');
                }
            }
        }

        renderGroupedConversations(grouped) {
            const groups = [
                { id: 'today', el: this.groupToday, list: this.listToday, items: grouped['Today'] || [] },
                { id: 'yesterday', el: this.groupYesterday, list: this.listYesterday, items: grouped['Yesterday'] || [] },
                { id: 'prev7', el: this.groupPrev7, list: this.listPrev7, items: grouped['Previous 7 Days'] || [] },
                { id: 'older', el: this.groupOlder, list: this.listOlder, items: grouped['Older'] || [] }
            ];

            let totalCount = 0;

            groups.forEach(g => {
                g.list.innerHTML = '';
                if (g.items.length > 0) {
                    g.el.classList.remove('hidden');
                    g.items.forEach(conv => {
                        const li = this.createConversationItemElement(conv);
                        g.list.appendChild(li);
                        totalCount++;
                    });
                } else {
                    g.el.classList.add('hidden');
                }
            });

            if (totalCount === 0) {
                this.historyEmpty.classList.remove('hidden');
            } else {
                this.historyEmpty.classList.add('hidden');
            }
        }

        createConversationItemElement(conv) {
            const li = document.createElement('li');
            li.className = `chat-item ${this.activeConversationId === conv.id ? 'active' : ''}`;
            li.setAttribute('data-conv-id', conv.id);

            li.innerHTML = `
                <i class="fa-regular fa-message chat-item-icon"></i>
                <span class="chat-item-title" title="${this.escapeHtml(conv.title)}">${this.escapeHtml(conv.title)}</span>
                <div class="chat-item-actions">
                    <button class="action-icon-btn rename-btn" title="Rename">
                        <i class="fa-solid fa-pen"></i>
                    </button>
                    <button class="action-icon-btn delete-btn" title="Delete">
                        <i class="fa-regular fa-trash-can"></i>
                    </button>
                </div>
            `;

            // Click conversation to load
            li.addEventListener('click', (e) => {
                if (e.target.closest('.action-icon-btn') || e.target.tagName === 'INPUT') return;
                this.selectConversation(conv.id);
            });

            // Rename button
            const renameBtn = li.querySelector('.rename-btn');
            renameBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.startInlineRename(li, conv);
            });

            // Delete button
            const deleteBtn = li.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openDeleteModal(conv.id);
            });

            return li;
        }

        startInlineRename(li, conv) {
            const titleSpan = li.querySelector('.chat-item-title');
            const currentTitle = conv.title;
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'rename-input';
            input.value = currentTitle;

            titleSpan.replaceWith(input);
            input.focus();
            input.select();

            const saveRename = async () => {
                const newTitle = input.value.trim();
                if (newTitle && newTitle !== currentTitle) {
                    try {
                        const res = await fetch(`/api/conversations/${conv.id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ title: newTitle })
                        });
                        const data = await res.json();
                        if (data.success) {
                            conv.title = newTitle;
                            titleSpan.textContent = newTitle;
                            titleSpan.title = newTitle;
                        }
                    } catch (err) {
                        console.error('Rename failed:', err);
                    }
                }
                if (input.parentNode) {
                    input.replaceWith(titleSpan);
                }
            };

            input.addEventListener('blur', saveRename);
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    input.blur();
                } else if (e.key === 'Escape') {
                    input.value = currentTitle;
                    input.blur();
                }
            });
        }

        openDeleteModal(convId) {
            this.deleteTargetId = convId;
            this.deleteModal.classList.remove('hidden');
        }

        closeDeleteModal() {
            this.deleteTargetId = null;
            this.deleteModal.classList.add('hidden');
        }

        async executeDeleteConversation() {
            if (!this.deleteTargetId) return;
            const convId = this.deleteTargetId;

            try {
                const res = await fetch(`/api/conversations/${convId}`, { method: 'DELETE' });
                const data = await res.json();
                if (data.success) {
                    // Remove from DOM
                    const el = document.querySelector(`.chat-item[data-conv-id="${convId}"]`);
                    if (el) el.remove();

                    // Remove from local list
                    this.conversations = this.conversations.filter(c => c.id !== convId);

                    // If deleted conversation was active, start fresh chat
                    if (this.activeConversationId === convId) {
                        this.startNewChat();
                    }

                    // Reload groupings
                    this.loadInitialConversations();
                }
            } catch (err) {
                console.error('Failed to delete conversation:', err);
            } finally {
                this.closeDeleteModal();
            }
        }

        async handleSearch(query) {
            const trimmed = query.trim();
            if (!trimmed) {
                this.searchClearBtn.classList.add('hidden');
                this.loadInitialConversations();
                return;
            }

            this.searchClearBtn.classList.remove('hidden');

            try {
                const res = await fetch(`/api/conversations/search?q=${encodeURIComponent(trimmed)}`);
                const data = await res.json();
                if (data.success) {
                    // Display search results in Today list and hide other groups
                    this.groupToday.classList.remove('hidden');
                    this.groupToday.querySelector('.group-title').textContent = `Search Results (${data.conversations.length})`;
                    this.listToday.innerHTML = '';

                    this.groupYesterday.classList.add('hidden');
                    this.groupPrev7.classList.add('hidden');
                    this.groupOlder.classList.add('hidden');

                    if (data.conversations.length === 0) {
                        this.historyEmpty.classList.remove('hidden');
                    } else {
                        this.historyEmpty.classList.add('hidden');
                        data.conversations.forEach(c => {
                            this.listToday.appendChild(this.createConversationItemElement(c));
                        });
                    }
                }
            } catch (err) {
                console.error('Search error:', err);
            }
        }

        // ---------------------------------------------------------------------
        // Chat Interactions & Messaging
        // ---------------------------------------------------------------------
        startNewChat() {
            this.activeConversationId = null;
            this.engine.clearMessages();
            this.engine.setWelcomeVisible(true);
            if (this.exportChatBtn) this.exportChatBtn.classList.add('hidden');

            // Deselect active item in sidebar
            document.querySelectorAll('.chat-item.active').forEach(el => el.classList.remove('active'));

            if (this.messageInput) {
                this.messageInput.value = '';
                this.handleInputResize();
                this.messageInput.focus();
            }

            this.closeMobileSidebar();
        }

        async selectConversation(convId) {
            if (this.activeConversationId === convId) {
                this.closeMobileSidebar();
                return;
            }

            this.activeConversationId = convId;
            this.engine.clearMessages();
            this.engine.setWelcomeVisible(false);

            // Update sidebar active highlights
            document.querySelectorAll('.chat-item').forEach(el => {
                if (el.getAttribute('data-conv-id') == convId) {
                    el.classList.add('active');
                } else {
                    el.classList.remove('active');
                }
            });

            this.closeMobileSidebar();

            try {
                const res = await fetch(`/api/conversations/${convId}`);
                const data = await res.json();
                if (data.success && data.conversation) {
                    const messages = data.conversation.messages || [];
                    messages.forEach(msg => {
                        if (msg.role === 'user') {
                            this.engine.appendUserMessage(msg.content, msg.formatted_time);
                        } else {
                            this.engine.appendBotMessage(
                                msg.content,
                                msg.id,
                                msg.rating,
                                msg.formatted_time,
                                false
                            );
                        }
                    });
                    this.engine.scrollToBottom();
                    if (this.exportChatBtn && messages.length > 0) {
                        this.exportChatBtn.classList.remove('hidden');
                    }
                }
            } catch (err) {
                console.error('Failed to load conversation details:', err);
            }
        }

        async exportCurrentChat() {
            if (!this.activeConversationId) return;
            try {
                const res = await fetch(`/api/conversations/${this.activeConversationId}`);
                const data = await res.json();
                if (data.success && data.conversation) {
                    const conv = data.conversation;
                    let markdown = `# ${conv.title}\n\n*Exported from NovaAI on ${new Date().toLocaleString()}*\n\n---\n\n`;
                    (conv.messages || []).forEach(m => {
                        const speaker = m.role === 'user' ? 'User' : 'NovaAI';
                        markdown += `### ${speaker} (${m.formatted_time || ''})\n\n${m.content}\n\n---\n\n`;
                    });

                    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${conv.title.toLowerCase().replace(/[^a-z0-9]/gi, '_')}.md`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }
            } catch (err) {
                console.error('Export failed:', err);
            }
        }

        async handleFormSubmit(e) {
            e.preventDefault();
            if (this.engine.isGenerating) {
                if (this.currentAbortController) {
                    this.currentAbortController.abort();
                }
                this.engine.stopGeneration();
                return;
            }
            const text = this.messageInput.value.trim();
            if (!text) return;

            // Clear input and reset height
            this.messageInput.value = '';
            this.handleInputResize();

            // Append user message immediately to viewport
            this.engine.appendUserMessage(text);
            this.engine.setTyping(true);

            this.currentAbortController = new AbortController();
            const signal = this.currentAbortController.signal;

            try {
                const res = await fetch('/api/chat/send-stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        conversation_id: this.activeConversationId,
                        message: text
                    }),
                    signal
                });

                if (!res.ok) {
                    this.engine.setTyping(false);
                    const errData = await res.json().catch(() => ({}));
                    this.engine.appendBotMessage(`⚠️ **Error**: ${errData.error || 'Failed to connect.'}`);
                    return;
                }

                const reader = res.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let botRow = null;
                let botContentEl = null;
                let accumulatedText = '';
                let messageId = null;

                this.engine.isGenerating = true;
                if (this.engine.onStateChange) this.engine.onStateChange(true);

                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed.startsWith('data: ')) continue;
                        const jsonStr = trimmed.substring(6);
                        try {
                            const payload = JSON.parse(jsonStr);

                            if (payload.meta) {
                                if (payload.is_new && payload.conversation_id) {
                                    this.activeConversationId = payload.conversation_id;
                                    this.loadInitialConversations();
                                }
                                continue;
                            }

                            if (payload.saved && payload.message_id) {
                                messageId = payload.message_id;
                                if (botRow) {
                                    botRow.setAttribute('data-message-id', messageId);
                                    this.engine.bindBotActions(botRow, accumulatedText, messageId);
                                }
                                continue;
                            }

                            if (payload.delta) {
                                this.engine.setTyping(false);
                                if (!botRow) {
                                    botRow = this.engine.createEmptyBotMessage();
                                    botContentEl = botRow.querySelector('.bot-content');
                                }
                                accumulatedText += payload.delta;
                                botContentEl.innerHTML = this.engine.renderMarkdown(accumulatedText);
                                this.engine.scrollToBottom();
                            }

                            if (payload.done) {
                                break;
                            }
                        } catch (errParse) {
                            console.error('SSE parse error:', errParse);
                        }
                    }
                }

                this.engine.setTyping(false);
                this.engine.isGenerating = false;
                if (this.engine.onStateChange) this.engine.onStateChange(false);

                if (botContentEl) {
                    botContentEl.innerHTML = this.engine.renderMarkdown(accumulatedText);
                    this.engine.applyPrism(botContentEl);
                }
                if (botRow && messageId) {
                    this.engine.bindBotActions(botRow, accumulatedText, messageId);
                }
                if (this.exportChatBtn) this.exportChatBtn.classList.remove('hidden');

            } catch (err) {
                if (err.name === 'AbortError') {
                    this.engine.setTyping(false);
                    this.engine.isGenerating = false;
                    if (this.engine.onStateChange) this.engine.onStateChange(false);
                } else {
                    this.engine.setTyping(false);
                    this.engine.isGenerating = false;
                    if (this.engine.onStateChange) this.engine.onStateChange(false);
                    this.engine.appendBotMessage(
                        '⚠️ **Network Error**: Unable to reach server. Please check your connection.'
                    );
                }
            }
        }

        async regenerateLastResponse() {
            if (!this.activeConversationId || this.engine.isGenerating) return;

            // Remove last assistant message element from UI
            const allBotRows = this.engine.messagesContainer.querySelectorAll('.bot-row');
            if (allBotRows.length > 0) {
                allBotRows[allBotRows.length - 1].remove();
            }

            this.engine.setTyping(true);

            try {
                const res = await fetch('/api/chat/regenerate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ conversation_id: this.activeConversationId })
                });
                const data = await res.json();
                this.engine.setTyping(false);

                if (res.ok && data.success) {
                    const botMsg = data.bot_message;
                    this.engine.appendBotMessage(
                        botMsg.content,
                        botMsg.id,
                        botMsg.rating,
                        botMsg.formatted_time,
                        true
                    );
                } else {
                    this.engine.appendBotMessage(
                        `⚠️ **Error**: ${data.error || 'Could not regenerate response.'}`
                    );
                }
            } catch (err) {
                this.engine.setTyping(false);
                this.engine.appendBotMessage('⚠️ **Network Error**: Regeneration request failed.');
            }
        }

        escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }
    }

    // Initialize application and expose to window
    window.NovaApp = new NovaChatApp();
});

