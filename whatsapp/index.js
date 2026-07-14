import makeWASocket, { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import express from 'express';
// QRCode removed - using pairing code instead
import axios from 'axios';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
app.use(express.json());

const PORT = 8001;
const FASTAPI_URL = 'http://localhost:8000';
const BOT_PHONE = process.env.MIDNIGHT_WA_BOT_PHONE || '';
const ALLOWED_SENDER = process.env.MIDNIGHT_WA_ALLOWED_SENDER || '';
let sock = null;
const sentMessageIds = new Set();
let isPairingMode = false;

// Endpoint to send WhatsApp messages from FastAPI
app.post('/send', async (req, res) => {
    const { to, text } = req.body;
    if (!sock) {
        return res.status(500).json({ error: 'WhatsApp socket not initialized' });
    }
    try {
        console.log(`[SEND] Attempting to send to: ${to}`);
        
        let resolvedJid = to;
        try {
            const [result] = await sock.onWhatsApp(to.replace(/@.*$/, ''));
            if (result && result.exists) {
                resolvedJid = result.jid;
                console.log(`[SEND] JID resolved: ${to} -> ${resolvedJid}`);
            }
        } catch (e) {
            console.log(`[SEND] onWhatsApp check failed, using original: ${e.message}`);
        }
        
        const sent = await sock.sendMessage(resolvedJid, { text: text });
        if (sent && sent.key && sent.key.id) {
            sentMessageIds.add(sent.key.id);
            console.log(`[SEND] Message sent successfully, id: ${sent.key.id}`);
            if (sentMessageIds.size > 1000) {
                const firstItem = sentMessageIds.values().next().value;
                sentMessageIds.delete(firstItem);
            }
        }
        res.json({ status: 'success', jid: resolvedJid });
    } catch (err) {
        console.error(`[SEND] Failed to send to ${to}:`, err.message);
        res.status(500).json({ error: err.message });
    }
});

async function connectToWhatsApp() {
    const authDir = path.join(__dirname, 'auth_info');
    const { state, saveCreds } = await useMultiFileAuthState(authDir);

    const makeWASocketFn = makeWASocket.default || makeWASocket;

    let version = [2, 3000, 1035194821]; // fallback version
    try {
        const { version: latestVersion, isLatest } = await fetchLatestBaileysVersion();
        console.log(`Using latest Baileys version: ${latestVersion.join('.')}, isLatest: ${isLatest}`);
        version = latestVersion;
    } catch (err) {
        console.error('Failed to fetch latest Baileys version, using fallback:', err.message);
    }

    console.log(`Auth registered: ${state.creds.registered}`);

    sock = makeWASocketFn({
        version,
        auth: state,
        printQRInTerminal: false,
        defaultQueryTimeoutMs: 60000,
        browser: ['Midnight Cowork', 'Chrome', '1.0.0']
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        console.log(`Connection update: ${JSON.stringify({ connection, hasQr: !!qr, statusCode: lastDisconnect?.error?.output?.statusCode })}`);

        if (qr && !state.creds.registered && !isPairingMode) {
            console.log('Requesting pairing code...');
            isPairingMode = true;
            try {
                const phoneNumber = BOT_PHONE;
                const code = await sock.requestPairingCode(phoneNumber);
                console.log(`Pairing code: ${code}`);
                await axios.post(`${FASTAPI_URL}/api/whatsapp/pairing-code`, { code: code });
            } catch (err) {
                console.error('Failed to request pairing code:', err.message);
                isPairingMode = false;
            }
        }

        if (connection === 'close') {
            const lastError = lastDisconnect?.error;
            const boomError = lastError;
            const statusCode = boomError?.output?.statusCode;
            console.log(`Connection closed with status: ${statusCode}`);
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            console.log('WhatsApp connection closed. Reconnecting:', shouldReconnect);
            
            try {
                if (!isPairingMode) {
                    const nextStatus = shouldReconnect ? 'connecting' : 'disconnected';
                    await axios.post(`${FASTAPI_URL}/api/whatsapp/status`, { status: nextStatus });
                }
            } catch (err) {}

            if (shouldReconnect) {
                setTimeout(connectToWhatsApp, 5000);
            }
        } else if (connection === 'open') {
            console.log('WhatsApp successfully connected!');
            isPairingMode = false;
            const phone = sock.user.id.split(':')[0];
            try {
                await axios.post(`${FASTAPI_URL}/api/whatsapp/status`, { 
                    status: 'connected', 
                    phone: phone 
                });
            } catch (err) {}
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        if (m.type !== 'notify') return;
        
        for (const message of m.messages) {
            console.log('DEBUG messages.upsert message:', JSON.stringify(message));
            const msgId = message.key.id;
            if (sentMessageIds.has(msgId)) {
                sentMessageIds.delete(msgId);
                continue;
            }

            let sender = message.key.remoteJid;
            if (message.key.senderPn) {
                sender = message.key.senderPn;
            }
            if (!sender || (!sender.endsWith('@s.whatsapp.net') && !sender.endsWith('@lid'))) continue;

            const cleanSender = sender.replace(/:.*@/, '@');

            // Security Whitelist
            const allowedSender = ALLOWED_SENDER;
            if (allowedSender && cleanSender !== allowedSender) {
                console.log(`[Security] Blocked message from unauthorized sender: ${cleanSender}`);
                continue;
            }

            if (message.key.fromMe) continue;
            
            let msgText = '';
            if (message.message) {
                msgText = message.message.conversation || 
                          (message.message.extendedTextMessage && message.message.extendedTextMessage.text) || 
                          '';
            }
            msgText = msgText.trim();
            if (!msgText) continue;

            console.log(`Forwarding message from ${cleanSender} to Midnight Cowork...`);

            try {
                const replyTo = message.key.senderPn || message.key.remoteJid;
                await axios.post(`${FASTAPI_URL}/api/whatsapp/message`, {
                    text: msgText,
                    sender: cleanSender,
                    reply_to: replyTo
                });
            } catch (err) {
                console.error('Failed to forward message to FastAPI:', err.message);
                await sock.sendMessage(message.key.remoteJid, { 
                    text: '⚠️ Terjadi kesalahan saat menghubungkan ke asisten Midnight Cowork.' 
                });
            }
        }
    });
}

connectToWhatsApp();

app.listen(PORT, () => {
    console.log(`WhatsApp Baileys bridge microservice running on port ${PORT}`);
});
