let chats = [];
let activeChatId = null;
let activeChatMessages = [];
let currentStreamReader = null;
let currentBlock = null;
let currentAssistantMessageElement = null;
let currentCodeWindowElement = null;

// Initialize Lucide icons and load data
document.addEventListener('DOMContentLoaded', () => {
    // Configure marked.js to use highlight.js for inline code blocks
    marked.setOptions({
        highlight: function(code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        },
        langPrefix: 'hljs language-'
    });

    // Close sidebar on page load if screen is mobile
    if (window.innerWidth < 1024) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.add('-translate-x-full');
        }
    }

    checkStatus();
    loadSettings();
    loadChats();
});

// Auto-grow input textarea
function autoGrowTextarea(element) {
    element.style.height = "auto";
    element.style.height = (element.scrollHeight) + "px";
}

// Quick insert prompt suggestion
function insertPrompt(text) {
    const input = document.getElementById('chat-input');
    input.value = text;
    autoGrowTextarea(input);
    input.focus();
}

// Handle Enter to send, Shift+Enter for newline
function handleInputKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Toggle Sidebar for mobile & desktop views
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const isMobile = window.innerWidth < 1024;
    
    if (isMobile) {
        // Mobile behavior: overlay drawer (uses translation)
        sidebar.classList.remove('w-0', 'lg:w-0', 'border-r-0');
        sidebar.classList.add('w-80');
        if (sidebar.classList.contains('-translate-x-full')) {
            sidebar.classList.remove('-translate-x-full');
        } else {
            sidebar.classList.add('-translate-x-full');
        }
    } else {
        // Desktop behavior: push/shrink content (uses width toggle + translation)
        sidebar.classList.remove('translate-x-0');
        if (sidebar.classList.contains('w-80') || sidebar.classList.contains('lg:w-80') || !sidebar.classList.contains('-translate-x-full')) {
            // Collapse
            sidebar.classList.remove('w-80', 'lg:w-80');
            sidebar.classList.add('w-0', 'lg:w-0', '-translate-x-full', 'border-r-0');
        } else {
            // Expand
            sidebar.classList.remove('w-0', 'lg:w-0', '-translate-x-full', 'border-r-0');
            sidebar.classList.add('w-80', 'lg:w-80');
        }
    }
}

// Check Backend Server and Open Interpreter status
async function checkStatus() {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        dot.className = 'w-2.5 h-2.5 rounded-full';
        
        if (data.interpreter_available) {
            dot.classList.add('bg-emerald-500', 'glow-green');
            text.textContent = 'Interpreter: Online';
            text.className = 'text-[10px] text-emerald-400 uppercase tracking-wider font-semibold';
            hideStatusBanner();
        } else {
            dot.classList.add('bg-amber-500');
            text.textContent = 'Interpreter: Offline';
            text.className = 'text-[10px] text-amber-400 uppercase tracking-wider font-semibold';
            showStatusBanner('Open Interpreter belum terinstal di server Python. Silakan jalankan `pip install open-interpreter` untuk mengaktifkan fungsionalitas penuh.');
        }
    } catch (error) {
        dot.className = 'w-2.5 h-2.5 rounded-full bg-red-500';
        text.textContent = 'Backend: Offline';
        text.className = 'text-[10px] text-red-500 uppercase tracking-wider font-semibold';
        showStatusBanner('Tidak dapat terhubung ke server backend FastAPI. Pastikan `start.bat` sedang berjalan.');
    }
}

function showStatusBanner(message) {
    const banner = document.getElementById('status-banner');
    const bannerMsg = document.getElementById('status-banner-msg');
    bannerMsg.innerHTML = message;
    banner.classList.remove('hidden');
}

function hideStatusBanner() {
    const banner = document.getElementById('status-banner');
    banner.classList.add('hidden');
}

// Load Settings from API
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        document.getElementById('setting-model').value = settings.model;
        if (settings.model === 'custom' || !['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo', 'claude-3-opus-20240229', 'claude-3-5-sonnet-20240620'].includes(settings.model)) {
            document.getElementById('setting-model').value = 'custom';
            document.getElementById('custom-model-container').classList.remove('hidden');
            document.getElementById('setting-custom-model').value = settings.model;
        } else {
            document.getElementById('custom-model-container').classList.add('hidden');
        }
        
        document.getElementById('setting-api-key').value = settings.api_key || '';
        document.getElementById('setting-system').value = settings.system_message || '';
        document.getElementById('setting-autorun').checked = settings.auto_run;
        
        // Update header badge
        const headerDot = document.getElementById('autorun-header-dot');
        const headerText = document.getElementById('autorun-header-text');
        if (settings.auto_run) {
            headerDot.className = 'w-1.5 h-1.5 rounded-full bg-emerald-500';
            headerText.textContent = 'Auto-Run: Aktif';
        } else {
            headerDot.className = 'w-1.5 h-1.5 rounded-full bg-amber-500';
            headerText.textContent = 'Auto-Run: Konfirmasi';
        }
    } catch (error) {
        console.error('Gagal memuat pengaturan:', error);
    }
}

// Save Settings to API
async function saveSettings() {
    const modelSelect = document.getElementById('setting-model').value;
    const customModel = document.getElementById('setting-custom-model').value.trim();
    const model = modelSelect === 'custom' ? customModel : modelSelect;
    const api_key = document.getElementById('setting-api-key').value.trim();
    const system_message = document.getElementById('setting-system').value.trim();
    const auto_run = document.getElementById('setting-autorun').checked;
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model, api_key, system_message, auto_run })
        });
        
        if (response.ok) {
            closeSettingsModal();
            loadSettings();
            alert('Pengaturan berhasil disimpan!');
        } else {
            alert('Gagal menyimpan pengaturan.');
        }
    } catch (error) {
        alert('Kesalahan jaringan saat menyimpan pengaturan.');
    }
}

function handleModelChange(value) {
    const customContainer = document.getElementById('custom-model-container');
    if (value === 'custom') {
        customContainer.classList.remove('hidden');
        document.getElementById('setting-custom-model').focus();
    } else {
        customContainer.classList.add('hidden');
    }
}

// Load Chat list from API
async function loadChats() {
    try {
        const response = await fetch('/api/chats');
        chats = await response.json();
        
        const listContainer = document.getElementById('chats-list');
        listContainer.innerHTML = '';
        
        if (chats.length === 0) {
            await createNewChat();
            return;
        }
        
        chats.forEach(chat => {
            const isActive = chat.id === activeChatId;
            const chatEl = document.createElement('div');
            chatEl.className = `group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${isActive ? 'bg-zinc-800 text-white font-medium' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850/60'}`;
            chatEl.setAttribute('onclick', `selectChat('${chat.id}')`);
            
            chatEl.innerHTML = `
                <div class="flex items-center gap-3 overflow-hidden">
                    <i data-lucide="message-square" class="w-4 h-4 shrink-0 text-zinc-500 group-hover:text-red-400 ${isActive ? 'text-red-400' : ''}"></i>
                    <span class="truncate text-sm pr-2">${chat.title}</span>
                </div>
                <button onclick="deleteChat('${chat.id}', event)" class="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-zinc-700 text-zinc-500 hover:text-red-400 transition-all">
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                </button>
            `;
            listContainer.appendChild(chatEl);
        });
        
        lucide.createIcons();
        
        if (!activeChatId && chats.length > 0) {
            selectChat(chats[0].id);
        }
    } catch (error) {
        console.error('Gagal memuat daftar chat:', error);
    }
}

// Select a Chat session
async function selectChat(chatId) {
    if (currentStreamReader) {
        alert('Harap tunggu atau batalkan proses eksekusi aktif sebelum berpindah percakapan.');
        return;
    }
    
    activeChatId = chatId;
    
    const listContainer = document.getElementById('chats-list');
    Array.from(listContainer.children).forEach(child => {
        child.className = child.innerHTML.includes(chatId) 
            ? 'group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all bg-zinc-800 text-white font-medium'
            : 'group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850/60';
    });
    
    try {
        const response = await fetch(`/api/chats/${chatId}`);
        const chat = await response.json();
        
        document.getElementById('active-chat-title').textContent = chat.title;
        activeChatMessages = chat.messages || [];
        renderMessages(activeChatMessages);
        
        document.getElementById('chat-input').disabled = false;
        document.getElementById('btn-send').disabled = false;
        document.getElementById('chat-input').focus();
    } catch (error) {
        console.error('Gagal mengambil data chat:', error);
    }
}

// Create new Chat session
async function createNewChat() {
    try {
        const response = await fetch('/api/chats', { method: 'POST' });
        const newChat = await response.json();
        
        activeChatId = newChat.id;
        await loadChats();
        selectChat(newChat.id);
    } catch (error) {
        console.error('Gagal membuat chat baru:', error);
    }
}

// Delete Chat session
async function deleteChat(chatId, event) {
    event.stopPropagation();
    
    if (confirm('Apakah Anda yakin ingin menghapus percakapan ini?')) {
        try {
            await fetch(`/api/chats/${chatId}`, { method: 'DELETE' });
            
            if (activeChatId === chatId) {
                activeChatId = null;
            }
            await loadChats();
        } catch (error) {
            console.error('Gagal menghapus chat:', error);
        }
    }
}

// Clear current chat messages
async function clearCurrentChat() {
    if (!activeChatId) return;
    if (confirm('Kosongkan semua riwayat pesan di sesi ini?')) {
        try {
            await fetch(`/api/chats/${activeChatId}`, { method: 'DELETE' });
            activeChatId = null;
            await loadChats();
        } catch (error) {
            console.error('Gagal mengosongkan chat:', error);
        }
    }
}

// Render Messages list
function renderMessages(messages) {
    const container = document.getElementById('messages-container');
    container.innerHTML = '';
    
    if (messages.length === 0) {
        renderWelcomeScreen();
        return;
    }
    
    let currentBubble = null;
    let currentCodeEl = null;
    
    messages.forEach((msg) => {
        if (msg.role === 'user') {
            currentBubble = null;
            renderUserMessage(msg.content);
        } else {
            if (!currentBubble) {
                currentBubble = createAssistantBubbleContainer();
                container.appendChild(currentBubble);
            }
            
            const contentArea = currentBubble.querySelector('.bubble-content');
            
            if (msg.role === 'assistant' && msg.type === 'message') {
                const textDiv = document.createElement('div');
                textDiv.className = 'prose-custom text-[15px] leading-relaxed text-zinc-100 mb-4 last:mb-0';
                textDiv.innerHTML = marked.parse(msg.content || '');
                contentArea.appendChild(textDiv);
                textDiv.querySelectorAll('pre code').forEach((el) => hljs.highlightElement(el));
            } 
            else if (msg.role === 'assistant' && msg.type === 'code') {
                const codeWin = createCodeWindowDOM(msg.content, msg.format || 'python');
                contentArea.appendChild(codeWin);
                currentCodeEl = codeWin;
            } 
            else if ((msg.role === 'computer' || msg.role === 'system') && msg.type === 'console') {
                if (currentCodeEl) {
                    const consoleEl = currentCodeEl.querySelector('.terminal-console');
                    consoleEl.textContent = msg.content;
                    consoleEl.classList.remove('hidden');
                } else {
                    const consoleDiv = document.createElement('pre');
                    consoleDiv.className = 'terminal-console';
                    consoleDiv.textContent = msg.content;
                    contentArea.appendChild(consoleDiv);
                }
            }
        }
    });
    
    container.scrollTop = container.scrollHeight;
}

// Render Welcome Screen
function renderWelcomeScreen() {
    const container = document.getElementById('messages-container');
    container.innerHTML = `
        <div class="max-w-3xl mx-auto text-center py-16 px-4 flex flex-col items-center justify-center h-full">
            <div class="w-16 h-16 rounded-2xl bg-red-600/10 flex items-center justify-center text-red-400 glow-red mb-6 animate-bounce">
                <i data-lucide="terminal" class="w-8 h-8"></i>
            </div>
            
            <h3 class="text-2xl font-bold text-white tracking-wide">Selamat Datang di Midnight Cowork</h3>
            <p class="text-zinc-400 text-sm mt-3 max-w-lg leading-relaxed">
                Asisten lokal bertenaga Open Interpreter yang siap membantu pekerjaan Anda. AI dapat menulis kode, mengontrol terminal, dan berinteraksi dengan file sistem.
            </p>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-2xl mt-12">
                <div onclick="insertPrompt('Tampilkan informasi RAM, CPU, dan OS PC saya')" class="p-4 rounded-xl border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-900/80 hover:border-red-500/30 cursor-pointer transition-all text-left flex flex-col justify-between group">
                    <div>
                        <i data-lucide="cpu" class="w-5 h-5 text-red-400 mb-3 group-hover:scale-110 transition-transform"></i>
                        <h4 class="font-semibold text-zinc-200 text-sm">Informasi Sistem</h4>
                        <p class="text-xs text-zinc-500 mt-1 leading-normal">Cek status RAM, CPU, dan spesifikasi OS komputer Anda.</p>
                    </div>
                    <span class="text-[10px] text-red-400 font-medium mt-3 inline-flex items-center gap-1">Coba prompt <i data-lucide="arrow-right" class="w-3 h-3"></i></span>
                </div>
                
                <div onclick="insertPrompt('Tampilkan daftar 10 file terbesar di folder Downloads saya')" class="p-4 rounded-xl border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-900/80 hover:border-red-500/30 cursor-pointer transition-all text-left flex flex-col justify-between group">
                    <div>
                        <i data-lucide="folder-search" class="w-5 h-5 text-rose-400 mb-3 group-hover:scale-110 transition-transform"></i>
                        <h4 class="font-semibold text-zinc-200 text-sm">Analisis File</h4>
                        <p class="text-xs text-zinc-500 mt-1 leading-normal">Mencari file berukuran besar atau mendata isi suatu direktori.</p>
                    </div>
                    <span class="text-[10px] text-rose-400 font-medium mt-3 inline-flex items-center gap-1">Coba prompt <i data-lucide="arrow-right" class="w-3 h-3"></i></span>
                </div>

                <div onclick="insertPrompt('Buatkan saya script Python sederhana untuk scrape cuaca Jakarta hari ini')" class="p-4 rounded-xl border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-900/80 hover:border-red-500/30 cursor-pointer transition-all text-left flex flex-col justify-between group">
                    <div>
                        <i data-lucide="code-2" class="w-5 h-5 text-orange-400 mb-3 group-hover:scale-110 transition-transform"></i>
                        <h4 class="font-semibold text-zinc-200 text-sm">Pembuatan Script</h4>
                        <p class="text-xs text-zinc-500 mt-1 leading-normal">Membuat script kustom untuk otomasi, scraping, atau pengolahan data.</p>
                    </div>
                    <span class="text-[10px] text-orange-400 font-medium mt-3 inline-flex items-center gap-1">Coba prompt <i data-lucide="arrow-right" class="w-3 h-3"></i></span>
                </div>
            </div>
        </div>
    `;
    lucide.createIcons();
}

// DOM Helper: Create User message
function renderUserMessage(text, animate = false) {
    const container = document.getElementById('messages-container');
    const msgEl = document.createElement('div');
    msgEl.className = `flex justify-end ${animate ? 'animate-fade-in' : ''}`;
    msgEl.innerHTML = `
        <div class="max-w-[80%] bg-gradient-to-br from-red-600 to-rose-600 text-white rounded-2xl rounded-tr-sm py-3 px-4 shadow-md text-[15px] leading-relaxed">
            ${escapeHTML(text).replace(/\n/g, '<br>')}
        </div>
    `;
    container.appendChild(msgEl);
}

// DOM Helper: Create Assistant bubble container
function createAssistantBubbleContainer(animate = false) {
    const container = document.createElement('div');
    container.className = `flex gap-4 max-w-[85%] ${animate ? 'animate-fade-in' : ''}`;
    container.innerHTML = `
        <div class="w-9 h-9 rounded-xl bg-zinc-850 border border-zinc-700/50 flex items-center justify-center text-red-400 shrink-0">
            <i data-lucide="bot" class="w-5 h-5"></i>
        </div>
        <div class="flex-1 bubble-content min-w-0"></div>
    `;
    setTimeout(() => lucide.createIcons(), 0);
    return container;
}

// DOM Helper: Create Code window frame
function createCodeWindowDOM(code, format) {
    const codeWin = document.createElement('div');
    codeWin.className = 'code-window';
    codeWin.innerHTML = `
        <div class="code-header">
            <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <span class="text-xs font-semibold uppercase tracking-wider text-zinc-400 font-mono">${format}</span>
            </div>
            <div class="flex items-center gap-3">
                <span class="text-[11px] text-zinc-500 font-medium font-mono code-status-badge">Mengeksekusi...</span>
                <button class="text-zinc-500 hover:text-zinc-300 transition-all p-1 hover:bg-zinc-800 rounded copy-btn" onclick="copyCode(this)">
                    <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                </button>
            </div>
        </div>
        <pre class="p-4 overflow-x-auto border-0 text-sm m-0"><code class="language-${format}">${escapeHTML(code)}</code></pre>
        <pre class="terminal-console hidden"></pre>
    `;
    setTimeout(() => {
        lucide.createIcons();
        hljs.highlightElement(codeWin.querySelector('code'));
    }, 0);
    return codeWin;
}

// Send Message action
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const messageText = input.value.trim();
    if (!messageText || !activeChatId || currentStreamReader) return;
    
    input.value = '';
    autoGrowTextarea(input);
    input.disabled = true;
    document.getElementById('btn-send').disabled = true;
    document.getElementById('btn-stop').classList.remove('hidden');
    
    const welcome = document.querySelector('#messages-container > div.max-w-3xl');
    if (welcome) {
        document.getElementById('messages-container').innerHTML = '';
    }
    
    renderUserMessage(messageText, true);
    
    const messagesContainer = document.getElementById('messages-container');
    currentAssistantMessageElement = createAssistantBubbleContainer(true);
    messagesContainer.appendChild(currentAssistantMessageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    const contentArea = currentAssistantMessageElement.querySelector('.bubble-content');
    
    const thinkingEl = document.createElement('div');
    thinkingEl.className = 'text-sm text-zinc-400 flex items-center gap-2 cursor-blink py-1';
    thinkingEl.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin text-red-400"></i> <span>Midnight Cowork sedang memproses...</span>`;
    contentArea.appendChild(thinkingEl);
    lucide.createIcons();
    
    currentBlock = null;
    currentCodeWindowElement = null;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: messageText,
                chat_id: activeChatId
            })
        });

        if (!response.ok) {
            throw new Error(`Server returned error status: ${response.status}`);
        }

        const reader = response.body.getReader();
        currentStreamReader = reader;
        const decoder = new TextDecoder();
        let buffer = '';

        if (thinkingEl.parentNode) {
            thinkingEl.parentNode.removeChild(thinkingEl);
        }

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    try {
                        const chunk = JSON.parse(dataStr);
                        processChunk(chunk, contentArea);
                    } catch (e) {
                        console.error('Failed to parse SSE JSON:', e, dataStr);
                    }
                }
            }
        }

    } catch (error) {
        console.error('Streaming error:', error);
        if (thinkingEl.parentNode) {
            thinkingEl.parentNode.removeChild(thinkingEl);
        }
        
        const errDiv = document.createElement('div');
        errDiv.className = 'p-3 rounded-lg bg-red-950/30 border border-red-900/50 text-red-400 text-xs mt-3 flex items-center gap-2';
        errDiv.innerHTML = `<i data-lucide="alert-circle" class="w-4 h-4 shrink-0"></i> <span>Terjadi kesalahan: ${error.message}</span>`;
        contentArea.appendChild(errDiv);
        lucide.createIcons();
    } finally {
        currentStreamReader = null;
        input.disabled = false;
        document.getElementById('btn-send').disabled = false;
        document.getElementById('btn-stop').classList.add('hidden');
        input.focus();
        loadChats();
    }
}

// Process single streaming chunk
function processChunk(chunk, parentContainer) {
    const messagesContainer = document.getElementById('messages-container');
    
    // 1. Text Message Block
    if (chunk.role === 'assistant' && chunk.type === 'message') {
        if (chunk.start === true || !currentBlock || currentBlock.type !== 'message') {
            finalizeCodeStatus();
            
            const textDiv = document.createElement('div');
            textDiv.className = 'prose-custom text-[15px] leading-relaxed text-zinc-100 mb-4 last:mb-0 cursor-blink';
            parentContainer.appendChild(textDiv);
            
            currentBlock = {
                type: 'message',
                element: textDiv,
                content: ''
            };
        }
        
        if (chunk.content) {
            currentBlock.content += chunk.content;
            currentBlock.element.innerHTML = marked.parse(currentBlock.content);
            currentBlock.element.querySelectorAll('pre code').forEach((el) => {
                if (!el.classList.contains('hljs')) {
                    hljs.highlightElement(el);
                }
            });
        }
        
        if (chunk.end === true) {
            currentBlock.element.classList.remove('cursor-blink');
            currentBlock = null;
        }
    }
    
    // 2. Code Block Window
    else if (chunk.role === 'assistant' && chunk.type === 'code') {
        if (chunk.start === true || !currentBlock || currentBlock.type !== 'code') {
            finalizeCodeStatus();
            
            const codeWin = createCodeWindowDOM('', chunk.format || 'python');
            parentContainer.appendChild(codeWin);
            
            currentCodeWindowElement = codeWin;
            
            currentBlock = {
                type: 'code',
                element: codeWin,
                codeContainer: codeWin.querySelector('code'),
                consoleContainer: codeWin.querySelector('.terminal-console'),
                statusBadge: codeWin.querySelector('.code-status-badge'),
                content: '',
                format: chunk.format
            };
        }
        
        if (chunk.content) {
            currentBlock.content += chunk.content;
            currentBlock.codeContainer.textContent = currentBlock.content;
            hljs.highlightElement(currentBlock.codeContainer);
        }
        
        if (chunk.end === true) {
            currentBlock.statusBadge.textContent = 'Menjalankan...';
            currentBlock = null;
        }
    }
    
    // 3. Active execution line
    else if (chunk.type === 'active_line') {
        if (currentCodeWindowElement) {
            const statusBadge = currentCodeWindowElement.querySelector('.code-status-badge');
            if (statusBadge) {
                statusBadge.textContent = `Menjalankan baris ${chunk.content}...`;
            }
        }
    }
    
    // 4. Computer Console output
    else if ((chunk.role === 'computer' || chunk.role === 'system') && chunk.type === 'console') {
        if (chunk.start === true || !currentBlock || currentBlock.type !== 'console') {
            let consoleEl = null;
            if (currentCodeWindowElement) {
                consoleEl = currentCodeWindowElement.querySelector('.terminal-console');
                consoleEl.classList.remove('hidden');
                consoleEl.textContent = '';
            } else {
                consoleEl = document.createElement('pre');
                consoleEl.className = 'terminal-console';
                parentContainer.appendChild(consoleEl);
            }
            
            currentBlock = {
                type: 'console',
                element: consoleEl,
                content: ''
            };
        }
        
        if (chunk.content) {
            currentBlock.content += chunk.content;
            currentBlock.element.textContent = currentBlock.content;
        }
        
        if (chunk.end === true) {
            if (currentCodeWindowElement) {
                const statusBadge = currentCodeWindowElement.querySelector('.code-status-badge');
                if (statusBadge) {
                    statusBadge.textContent = 'Selesai';
                    statusBadge.className = 'text-[11px] text-emerald-400 font-semibold font-mono code-status-badge';
                }
            }
            currentBlock = null;
        }
    }
    
    // 5. General Error (during run)
    else if (chunk.type === 'error') {
        if (currentCodeWindowElement) {
            const consoleEl = currentCodeWindowElement.querySelector('.terminal-console');
            consoleEl.classList.remove('hidden');
            consoleEl.classList.add('error-output');
            consoleEl.textContent += `\nError: ${chunk.content}`;
            
            const statusBadge = currentCodeWindowElement.querySelector('.code-status-badge');
            if (statusBadge) {
                statusBadge.textContent = 'Error';
                statusBadge.className = 'text-[11px] text-red-400 font-semibold font-mono code-status-badge';
            }
        } else {
            const errDiv = document.createElement('div');
            errDiv.className = 'p-3 rounded-lg bg-red-950/30 border border-red-900/50 text-red-400 text-xs mt-3 flex items-center gap-2';
            errDiv.innerHTML = `<i data-lucide="alert-circle" class="w-4 h-4"></i> <span>Error: ${chunk.content}</span>`;
            parentContainer.appendChild(errDiv);
            lucide.createIcons();
        }
        currentBlock = null;
    }
    
    // Auto-scroll
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Helpers
function finalizeCodeStatus() {
    if (currentCodeWindowElement) {
        const badge = currentCodeWindowElement.querySelector('.code-status-badge');
        if (badge && badge.textContent === 'Mengeksekusi...') {
            badge.textContent = 'Selesai';
            badge.className = 'text-[11px] text-emerald-400 font-semibold font-mono code-status-badge';
        }
    }
}

function stopGeneration() {
    if (currentStreamReader) {
        currentStreamReader.cancel();
        currentStreamReader = null;
    }
}

// Copy Code Helper
function copyCode(btn) {
    const codeEl = btn.closest('.code-window').querySelector('code');
    navigator.clipboard.writeText(codeEl.textContent).then(() => {
        const icon = btn.querySelector('i');
        btn.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400"></i>';
        lucide.createIcons();
        setTimeout(() => {
            btn.innerHTML = '<i data-lucide="copy" class="w-3.5 h-3.5"></i>';
            lucide.createIcons();
        }, 2000);
    });
}

function escapeHTML(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Modal Controls
function openSettingsModal() {
    loadSettings();
    const modal = document.getElementById('settings-modal');
    const panel = document.getElementById('settings-modal-panel');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        panel.classList.remove('translate-y-4');
    }, 50);
}

function closeSettingsModal() {
    const modal = document.getElementById('settings-modal');
    const panel = document.getElementById('settings-modal-panel');
    modal.classList.add('opacity-0');
    panel.classList.add('translate-y-4');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

function togglePasswordVisibility(id, btn) {
    const input = document.getElementById(id);
    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = '<i data-lucide="eye-off" class="w-4 h-4"></i>';
    } else {
        input.type = 'password';
        btn.innerHTML = '<i data-lucide="eye" class="w-4 h-4"></i>';
    }
    lucide.createIcons();
}

function shutdownServer() {
    const modal = document.getElementById('confirm-modal');
    const panel = document.getElementById('confirm-modal-panel');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        panel.classList.remove('translate-y-4');
    }, 50);
}

function closeConfirmModal() {
    const modal = document.getElementById('confirm-modal');
    const panel = document.getElementById('confirm-modal-panel');
    modal.classList.add('opacity-0');
    panel.classList.add('translate-y-4');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

async function executeShutdown() {
    closeConfirmModal();
    try {
        const response = await fetch('/api/shutdown', { method: 'POST' });
        if (response.ok) {
            document.body.innerHTML = `
                <div class="h-screen w-screen bg-zinc-950 flex flex-col items-center justify-center p-4 text-center">
                    <div class="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center text-red-500 mb-6">
                        <i data-lucide="power" class="w-8 h-8"></i>
                    </div>
                    <h3 class="text-xl font-bold text-white mb-2">Server Dimatikan</h3>
                    <p class="text-sm text-zinc-400 max-w-sm">Proses backend FastAPI telah dihentikan. Anda sekarang dapat menutup tab ini.</p>
                </div>
            `;
            lucide.createIcons();
        } else {
            alert('Gagal mematikan server.');
        }
    } catch (error) {
        document.body.innerHTML = `
            <div class="h-screen w-screen bg-zinc-950 flex flex-col items-center justify-center p-4 text-center">
                <div class="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center text-red-500 mb-6">
                    <i data-lucide="power" class="w-8 h-8"></i>
                </div>
                <h3 class="text-xl font-bold text-white mb-2">Server Dimatikan</h3>
                <p class="text-sm text-zinc-400 max-w-sm">Proses backend FastAPI telah dihentikan. Anda sekarang dapat menutup tab ini.</p>
            </div>
        `;
        lucide.createIcons();
    }
}
