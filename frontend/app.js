// Production API URL will be injected via environment or detected
const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? "http://127.0.0.1:8000"
    : "https://bio-ai-daily-update.onrender.com"; // Matches your Render URL

document.getElementById('refreshBtn').addEventListener('click', async () => {
    const loader = document.getElementById('loader');
    const refreshBtn = document.getElementById('refreshBtn');
    const aiTopic = document.getElementById('aiTopic').value || "AI and Machine Learning";
    const bioTopic = document.getElementById('bioTopic').value || "Single-cell cancer bioinformatics";

    loader.style.display = 'block';
    refreshBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/updates/research?ai_topic=${encodeURIComponent(aiTopic)}&bio_topic=${encodeURIComponent(bioTopic)}`, { method: 'POST' });
        if (response.ok) {
            loadLatestUpdate();
        } else {
            alert('Failed to trigger research. Make sure the backend is running and the API key is set.');
        }
    } catch (err) {
        console.error(err);
        alert('Server unreachable. Start FastAPI backend first.');
    } finally {
        loader.style.display = 'none';
        refreshBtn.disabled = false;
    }
});

async function loadLatestUpdate() {
    try {
        const response = await fetch(`${API_URL}/updates/latest`);
        if (response.ok) {
            const data = await response.json();
            renderPapers(data.ai_papers, 'ai-papers');
            renderPapers(data.bio_papers, 'bio-papers');

            // Handle gap analysis
            const gapSection = document.getElementById('gap-analysis-section');
            const gapContent = document.getElementById('gap-content');
            if (data.overall_gap_analysis) {
                gapSection.style.display = 'block';
                gapContent.innerHTML = `<div style="white-space: pre-wrap;">${data.overall_gap_analysis}</div>`;
            }
        }
    } catch (err) {
        console.warn("No updates found yet.");
    }
}

document.getElementById('webSearchBtn').addEventListener('click', async () => {
    const loader = document.getElementById('loader');
    const webSearchBtn = document.getElementById('webSearchBtn');
    const webContent = document.getElementById('web-research-content');
    const aiTopic = document.getElementById('aiTopic').value || "AI and Bioinformatics";

    loader.style.display = 'block';
    webSearchBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/research/web?query=${encodeURIComponent(aiTopic)}`);
        if (response.ok) {
            const data = await response.json();
            webContent.innerHTML = `<div style="white-space: pre-wrap;">${data.data}</div>`;
        } else {
            alert('Web search failed.');
        }
    } catch (err) {
        console.error(err);
        alert('Server unreachable.');
    } finally {
        loader.style.display = 'none';
        webSearchBtn.disabled = false;
    }
});

let currentPaperId = null;

function renderPapers(papers, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    papers.forEach((paper, index) => {
        const card = document.createElement('div');
        card.className = 'paper-card';
        card.style.animationDelay = `${index * 0.1}s`;

        const insights = paper.insights || { summary: 'No insights generated.', key_technologies: [], research_gaps: [], multimodal_insights: '' };

        card.innerHTML = `
            <div class="paper-category">${paper.category || 'Research'}</div>
            <h3>${paper.title}</h3>
            <div class="paper-meta">
                <span>👤 ${paper.authors.slice(0, 3).join(', ')}${paper.authors.length > 3 ? ' et al.' : ''}</span> | 
                <span>📅 ${new Date(paper.published_date).toLocaleDateString()}</span>
            </div>
            
            <div class="summary-box">
                "${insights.summary}"
            </div>

            <div style="margin-bottom: 1rem;">
                <strong>Key Technologies:</strong><br>
                ${insights.key_technologies.map(t => `<span class="tech-tag">${t}</span>`).join(' ')}
            </div>

            <div class="insight-grid">
                <div class="insight-box">
                    <div class="insight-label">🔬 Research Gaps</div>
                    <ul>
                        ${insights.research_gaps.map(g => `<li>${g}</li>`).join('')}
                    </ul>
                </div>
            </div>

            ${insights.multimodal_insights ? `
                <div style="margin-top:1rem; border-top: 1px solid var(--glass-border); padding-top: 0.5rem; font-size: 0.9rem;">
                    <strong>🖼️ Visual Analysis:</strong> ${insights.multimodal_insights}
                </div>
            ` : ''}

            <div style="margin-top: 1.5rem; display: flex; gap: 1rem; align-items: center; justify-content: space-between;">
                <a href="${paper.url}" target="_blank" style="color: var(--primary); text-decoration: none; font-weight: bold;">Read Paper →</a>
                <button class="chat-btn" onclick="openChat(${paper.id}, '${paper.title.replace(/'/g, "\\'")}')">💬 Ask AI</button>
            </div>
        `;
        container.appendChild(card);
    });
}

// Chat Logic
const modal = document.getElementById("chatModal");
const closeModal = document.querySelector(".close-modal");

window.openChat = function (paperId, title) {
    currentPaperId = paperId;
    document.getElementById("modalPaperTitle").textContent = `Chat about: ${title}`;
    document.getElementById("chatMessages").innerHTML = '<div class="message ai">Hi! I\'ve analyzed this paper. What would you like to know?</div>';
    modal.style.display = "block";
};

closeModal.onclick = () => modal.style.display = "none";
window.onclick = (event) => { if (event.target == modal) modal.style.display = "none"; };

document.getElementById('sendChatBtn').addEventListener('click', async () => {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;

    appendMessage('user', message);
    input.value = '';

    try {
        const response = await fetch(`${API_URL}/papers/${currentPaperId}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await response.json();
        appendMessage('ai', data.answer);
    } catch (err) {
        appendMessage('ai', "Error: Could not reach the AI brain.");
    }
});

function appendMessage(role, text) {
    const chatMessages = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.textContent = text;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Initial load
loadLatestUpdate();
