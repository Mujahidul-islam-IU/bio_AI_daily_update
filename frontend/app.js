// =====================================================
// BioAI Daily Update — Frontend Application
// =====================================================

const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? "http://127.0.0.1:8000"
    : "https://bio-ai-daily-update.onrender.com";

// ─── Utility: Render Markdown from LLM output ──────
function renderMarkdown(text) {
    if (!text) return '';
    try {
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                breaks: true,
                gfm: true,
                sanitize: false
            });
            return marked.parse(text);
        }
    } catch (e) {
        console.warn('Marked.js parse error:', e);
    }
    // Fallback: basic markdown rendering
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

// ─── Navigation ─────────────────────────────────────
const navLinks = document.querySelectorAll('.nav-link');
const sections = document.querySelectorAll('.content-section');
const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menuToggle');
const closeSidebar = document.getElementById('closeSidebar');
const mobileOverlay = document.getElementById('mobileOverlay');

function switchSection(sectionId) {
    sections.forEach(s => s.classList.remove('active'));
    navLinks.forEach(l => l.classList.remove('active'));
    
    const target = document.getElementById(`section-${sectionId}`);
    if (target) target.classList.add('active');
    
    navLinks.forEach(l => {
        if (l.dataset.section === sectionId) l.classList.add('active');
    });
    
    // Load section data
    if (sectionId === 'history') loadHistory();
    if (sectionId === 'bookmarks') loadBookmarks();
    
    // Close mobile sidebar
    closeMobileSidebar();
}

navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        switchSection(link.dataset.section);
    });
});

// Mobile sidebar toggle
menuToggle.addEventListener('click', () => {
    sidebar.classList.add('open');
    mobileOverlay.classList.add('active');
});

function closeMobileSidebar() {
    sidebar.classList.remove('open');
    mobileOverlay.classList.remove('active');
}

closeSidebar.addEventListener('click', closeMobileSidebar);
mobileOverlay.addEventListener('click', closeMobileSidebar);

// ─── Theme Toggle ───────────────────────────────────
const themeToggle = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('bioai-theme', theme);
    themeIcon.textContent = theme === 'dark' ? '🌙' : '☀️';
    document.querySelector('.theme-label').textContent = theme === 'dark' ? 'Dark Mode' : 'Light Mode';
}

// Load saved theme
const savedTheme = localStorage.getItem('bioai-theme') || 'dark';
setTheme(savedTheme);

themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    setTheme(current === 'dark' ? 'light' : 'dark');
});

// ─── Status Indicator ───────────────────────────────
function setStatus(text, color = 'var(--accent-success)') {
    const dot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    dot.style.background = color;
    statusText.textContent = text;
}

// ─── Loader ─────────────────────────────────────────
function showLoader(text = 'Processing...') {
    const loader = document.getElementById('loader');
    loader.classList.add('visible');
    loader.querySelector('.loader-text').textContent = text;
}

function hideLoader() {
    document.getElementById('loader').classList.remove('visible');
}

// ─── Research Trigger ───────────────────────────────
document.getElementById('refreshBtn').addEventListener('click', async () => {
    const refreshBtn = document.getElementById('refreshBtn');
    const aiTopic = document.getElementById('aiTopic').value || "AI and Machine Learning";
    const bioTopic = document.getElementById('bioTopic').value || "Single-cell cancer bioinformatics";

    showLoader('Fetching papers from arXiv, PubMed & bioRxiv...');
    refreshBtn.disabled = true;
    setStatus('Researching...', 'var(--accent-gold)');

    // Clear previous results
    document.getElementById('ai-papers').innerHTML = '<div class="empty-state">Searching...</div>';
    document.getElementById('bio-papers').innerHTML = '<div class="empty-state">Searching...</div>';
    document.getElementById('biorxiv-papers').innerHTML = '<div class="empty-state">Searching...</div>';
    document.getElementById('nature-papers').innerHTML = '<div class="empty-state">Searching...</div>';

    try {
        const response = await fetch(`${API_URL}/updates/research?ai_topic=${encodeURIComponent(aiTopic)}&bio_topic=${encodeURIComponent(bioTopic)}`, { method: 'POST' });
        if (response.ok) {
            const result = await response.json();
            // Show gap analysis from response
            if (result.gap_analysis) {
                const gapSection = document.getElementById('gap-analysis-section');
                gapSection.style.display = 'block';
                document.getElementById('gap-content').innerHTML = renderMarkdown(result.gap_analysis);
            }
            await loadLatestUpdate();
            setStatus('Ready', 'var(--accent-success)');
        } else {
            const err = await response.text();
            console.error('Research error:', err);
            setStatus('Error', 'var(--accent-rose)');
            alert('Research failed. Check that the backend is running and API keys are configured.');
        }
    } catch (err) {
        console.error(err);
        setStatus('Offline', 'var(--accent-rose)');
        alert('Server unreachable. Start the FastAPI backend first.');
    } finally {
        hideLoader();
        refreshBtn.disabled = false;
    }
});

// ─── Load Latest Update ─────────────────────────────
async function loadLatestUpdate() {
    try {
        const response = await fetch(`${API_URL}/updates/latest`);
        if (response.ok) {
            const data = await response.json();
            renderPapers(data.ai_papers, 'ai-papers');
            renderPapers(data.bio_papers, 'bio-papers');
            renderPapers(data.biorxiv_papers || [], 'biorxiv-papers');
            renderPapers(data.nature_papers || [], 'nature-papers');

            // Gap analysis
            const gapSection = document.getElementById('gap-analysis-section');
            if (data.overall_gap_analysis) {
                gapSection.style.display = 'block';
                document.getElementById('gap-content').innerHTML = renderMarkdown(data.overall_gap_analysis);
            }
        }
    } catch (err) {
        console.warn("No updates found yet.");
    }
}

// ─── Web Search ─────────────────────────────────────
document.getElementById('webSearchBtn').addEventListener('click', async () => {
    const webSearchBtn = document.getElementById('webSearchBtn');
    const webContent = document.getElementById('web-research-content');
    const aiTopic = document.getElementById('aiTopic').value || "AI and Bioinformatics";

    showLoader('Searching the web with Tavily AI...');
    webSearchBtn.disabled = true;
    setStatus('Synthesizing...', 'var(--accent-cyan)');

    try {
        const response = await fetch(`${API_URL}/research/web?query=${encodeURIComponent(aiTopic)}`);
        if (response.ok) {
            const data = await response.json();
            webContent.innerHTML = `<div class="markdown-body">${renderMarkdown(data.data)}</div>`;
            setStatus('Ready', 'var(--accent-success)');
        } else {
            webContent.innerHTML = '<p class="placeholder-text">Web search failed. Check Tavily API key.</p>';
            setStatus('Error', 'var(--accent-rose)');
        }
    } catch (err) {
        console.error(err);
        webContent.innerHTML = '<p class="placeholder-text">Server unreachable.</p>';
        setStatus('Offline', 'var(--accent-rose)');
    } finally {
        hideLoader();
        webSearchBtn.disabled = false;
    }
});

// ─── Render Papers ──────────────────────────────────
function renderPapers(papers, containerId) {
    const container = document.getElementById(containerId);
    
    if (!papers || papers.length === 0) {
        container.innerHTML = '<div class="empty-state">No papers found for this query.</div>';
        return;
    }
    
    container.innerHTML = '';

    papers.forEach((paper, index) => {
        const card = document.createElement('div');
        card.className = 'paper-card';
        card.style.animationDelay = `${index * 0.08}s`;

        const insights = paper.insights || { summary: 'No insights generated.', key_technologies: [], research_gaps: [], multimodal_insights: '' };
        
        // Determine category class
        let catClass = 'ai';
        if (paper.category === 'Bioinformatics') catClass = 'bio';
        if (paper.category === 'Preprint') catClass = 'preprint';
        if (paper.category === 'Nature / Top Journals') catClass = 'nature';

        const authorsDisplay = paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ' et al.' : '');
        const dateStr = new Date(paper.published_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });

        card.innerHTML = `
            <div class="paper-card-top">
                <span class="paper-category ${catClass}">${paper.category || 'Research'}</span>
                <button class="bookmark-btn" onclick="toggleBookmark(${paper.id}, this)" title="Bookmark this paper">☆</button>
            </div>
            <h3>${paper.title}</h3>
            <div class="paper-meta">
                <span>👤 ${authorsDisplay}</span>
                <span>📅 ${dateStr}</span>
                <span>📡 ${paper.source || ''}</span>
            </div>
            
            <div class="summary-box">
                ${renderMarkdown(insights.summary)}
            </div>

            ${insights.key_technologies && insights.key_technologies.length > 0 && insights.key_technologies[0] !== 'Manual Review Required' ? `
                <div class="tech-tags">
                    ${insights.key_technologies.map(t => `<span class="tech-tag">${t}</span>`).join('')}
                </div>
            ` : ''}

            ${insights.research_gaps && insights.research_gaps.length > 0 && insights.research_gaps[0] !== 'Check paper for details' ? `
                <div class="gaps-section">
                    <div class="gaps-label">🔬 Research Gaps</div>
                    <ul>
                        ${insights.research_gaps.map(g => `<li>${g}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}

            ${insights.multimodal_insights ? `
                <div style="margin-top:0.75rem; font-size: 0.85rem; color: var(--text-secondary);">
                    <strong>🖼️ Visual:</strong> ${insights.multimodal_insights}
                </div>
            ` : ''}

            <div class="paper-actions">
                <a href="${paper.url}" target="_blank" class="paper-link">Read Paper →</a>
                <button class="chat-btn" onclick="openChat(${paper.id}, '${paper.title.replace(/'/g, "\\'")}')">💬 Ask AI</button>
            </div>
        `;
        container.appendChild(card);
    });
}

// ─── Bookmarks ──────────────────────────────────────
window.toggleBookmark = async function(paperId, btn) {
    try {
        const response = await fetch(`${API_URL}/papers/${paperId}/bookmark`, { method: 'POST' });
        if (response.ok) {
            const data = await response.json();
            btn.textContent = data.bookmarked ? '★' : '☆';
            btn.style.color = data.bookmarked ? 'var(--accent-gold)' : '';
        }
    } catch (err) {
        console.error('Bookmark error:', err);
    }
};

async function loadBookmarks() {
    const list = document.getElementById('bookmarks-list');
    try {
        const response = await fetch(`${API_URL}/papers/bookmarks`);
        if (response.ok) {
            const bookmarks = await response.json();
            if (bookmarks.length === 0) {
                list.innerHTML = '<div class="empty-state">No bookmarks yet. Star papers you want to revisit.</div>';
                return;
            }
            list.innerHTML = '';
            bookmarks.forEach(p => {
                const card = document.createElement('div');
                card.className = 'paper-card';
                let catClass = 'ai';
                if (p.category === 'Bioinformatics') catClass = 'bio';
                if (p.category === 'Preprint') catClass = 'preprint';
                if (p.category === 'Nature / Top Journals') catClass = 'nature';
                
                card.innerHTML = `
                    <div class="paper-card-top">
                        <span class="paper-category ${catClass}">${p.category}</span>
                        <button class="bookmark-btn" style="color: var(--accent-gold);" onclick="toggleBookmark(${p.id}, this)">★</button>
                    </div>
                    <h3>${p.title}</h3>
                    <div class="summary-box">${renderMarkdown(p.insight_summary || '')}</div>
                    <div class="paper-actions">
                        <a href="${p.url}" target="_blank" class="paper-link">Read Paper →</a>
                        <button class="chat-btn" onclick="openChat(${p.id}, '${p.title.replace(/'/g, "\\'")}')">💬 Ask AI</button>
                    </div>
                `;
                list.appendChild(card);
            });
        }
    } catch (err) {
        list.innerHTML = '<div class="empty-state">Could not load bookmarks.</div>';
    }
}

// ─── History ────────────────────────────────────────
async function loadHistory() {
    const list = document.getElementById('history-list');
    const detail = document.getElementById('history-detail');
    detail.style.display = 'none';
    list.style.display = 'flex';
    
    try {
        const response = await fetch(`${API_URL}/updates/history`);
        if (response.ok) {
            const history = await response.json();
            if (history.length === 0) {
                list.innerHTML = '<div class="empty-state">No research history yet. Run a research query first.</div>';
                return;
            }
            list.innerHTML = '';
            history.forEach((item, index) => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.style.animationDelay = `${index * 0.05}s`;
                const date = new Date(item.date);
                div.innerHTML = `
                    <div class="history-info">
                        <h3>📋 Research Session #${item.id}</h3>
                        <p>${date.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })} at ${date.toLocaleTimeString()}</p>
                        ${item.gap_analysis_preview ? `<p style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-muted);">${item.gap_analysis_preview}...</p>` : ''}
                    </div>
                    <div class="history-meta">
                        <span class="history-badge">${item.paper_count} papers</span>
                    </div>
                `;
                div.addEventListener('click', () => loadHistoryDetail(item.id));
                list.appendChild(div);
            });
        }
    } catch (err) {
        list.innerHTML = '<div class="empty-state">Could not load history.</div>';
    }
}

async function loadHistoryDetail(updateId) {
    const list = document.getElementById('history-list');
    const detail = document.getElementById('history-detail');
    const content = document.getElementById('history-detail-content');
    
    list.style.display = 'none';
    detail.style.display = 'block';
    content.innerHTML = '<div class="empty-state">Loading...</div>';
    
    try {
        const response = await fetch(`${API_URL}/updates/${updateId}`);
        if (response.ok) {
            const data = await response.json();
            let html = `
                <div class="section-header" style="margin-top: 1rem;">
                    <h2>📋 Research Session #${data.id}</h2>
                    <p>${new Date(data.date).toLocaleString()}</p>
                    <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
                        <a href="${API_URL}/updates/${updateId}/export" target="_blank" class="btn btn-ghost">📥 Export Markdown</a>
                    </div>
                </div>
            `;
            
            if (data.overall_gap_analysis) {
                html += `
                    <div class="card gap-card" style="margin-top: 1.5rem;">
                        <div class="card-header"><h2>🔍 Gap Analysis</h2></div>
                        <div class="card-body markdown-body">${renderMarkdown(data.overall_gap_analysis)}</div>
                    </div>
                `;
            }
            
            html += '<div class="paper-list" style="margin-top: 1.5rem;">';
            data.papers.forEach(p => {
                let catClass = 'ai';
                if (p.category === 'Bioinformatics') catClass = 'bio';
                if (p.category === 'Preprint') catClass = 'preprint';
                if (p.category === 'Nature / Top Journals') catClass = 'nature';
                
                html += `
                    <div class="paper-card">
                        <div class="paper-card-top">
                            <span class="paper-category ${catClass}">${p.category}</span>
                        </div>
                        <h3>${p.title}</h3>
                        <p class="paper-meta">👤 ${p.authors}</p>
                        <div class="summary-box">${renderMarkdown(p.insight_summary || '')}</div>
                        ${p.key_technologies && p.key_technologies.length > 0 ? `
                            <div class="tech-tags">${p.key_technologies.map(t => `<span class="tech-tag">${t}</span>`).join('')}</div>
                        ` : ''}
                        <div class="paper-actions">
                            <a href="${p.url}" target="_blank" class="paper-link">Read Paper →</a>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            content.innerHTML = html;
        }
    } catch (err) {
        content.innerHTML = '<div class="empty-state">Could not load details.</div>';
    }
}

document.getElementById('backToHistory').addEventListener('click', () => {
    document.getElementById('history-list').style.display = 'flex';
    document.getElementById('history-detail').style.display = 'none';
});

// ─── Chat Modal (with session persistence) ──────────
let currentPaperId = null;
const modal = document.getElementById("chatModal");
const closeModalBtn = document.getElementById("closeModalBtn");

window.openChat = async function (paperId, title) {
    currentPaperId = paperId;
    document.getElementById("modalPaperTitle").textContent = `Chat: ${title}`;
    
    const chatMessages = document.getElementById("chatMessages");
    chatMessages.innerHTML = '<div class="message ai">Loading chat history...</div>';
    modal.style.display = "block";
    document.body.style.overflow = 'hidden';
    
    // Load chat history for this paper
    try {
        const response = await fetch(`${API_URL}/papers/${paperId}/chat/history`);
        if (response.ok) {
            const history = await response.json();
            chatMessages.innerHTML = '';
            
            if (history.length === 0) {
                chatMessages.innerHTML = '<div class="message ai"><div class="markdown-body">Hi! I\'ve analyzed this paper. What would you like to know?</div></div>';
            } else {
                history.forEach(msg => {
                    appendMessage(msg.role, msg.content);
                });
            }
        } else {
            chatMessages.innerHTML = '<div class="message ai"><div class="markdown-body">Hi! I\'ve analyzed this paper. What would you like to know?</div></div>';
        }
    } catch (err) {
        chatMessages.innerHTML = '<div class="message ai"><div class="markdown-body">Hi! I\'ve analyzed this paper. Ask me anything!</div></div>';
    }
    
    // Focus input
    setTimeout(() => document.getElementById('chatInput').focus(), 200);
};

closeModalBtn.addEventListener('click', closeChat);
window.addEventListener('click', (event) => { 
    if (event.target === modal) closeChat(); 
});

function closeChat() {
    modal.style.display = "none";
    document.body.style.overflow = '';
}

// Send chat message
async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message || !currentPaperId) return;

    appendMessage('user', message);
    input.value = '';
    
    // Show typing indicator
    const typingId = appendMessage('typing', 'AI is thinking...');

    try {
        const response = await fetch(`${API_URL}/papers/${currentPaperId}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        // Remove typing indicator
        removeMessage(typingId);
        
        if (response.ok) {
            const data = await response.json();
            appendMessage('ai', data.answer);
        } else {
            const errData = await response.text();
            appendMessage('ai', `Sorry, something went wrong. Error: ${errData}`);
        }
    } catch (err) {
        removeMessage(typingId);
        appendMessage('ai', "Error: Could not reach the AI. Make sure the backend is running.");
    }
}

document.getElementById('sendChatBtn').addEventListener('click', sendChatMessage);
document.getElementById('chatInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

let messageCounter = 0;

function appendMessage(role, text) {
    const chatMessages = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    const msgId = `msg-${++messageCounter}`;
    msgDiv.id = msgId;
    msgDiv.className = `message ${role}`;
    
    if (role === 'ai') {
        msgDiv.innerHTML = `<div class="markdown-body">${renderMarkdown(text)}</div>`;
    } else if (role === 'typing') {
        msgDiv.textContent = text;
    } else {
        msgDiv.textContent = text;
    }
    
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgId;
}

function removeMessage(msgId) {
    const msg = document.getElementById(msgId);
    if (msg) msg.remove();
}

// ─── Initial Load ───────────────────────────────────
loadLatestUpdate();
