let currentDish = null;

document.addEventListener("DOMContentLoaded", function() {
    initStarLogic();
    initResizer(); // START RESIZER
});

// --- RESIZER LOGIC ---
function initResizer() {
    const resizer = document.getElementById('resizer');
    const sidebar = document.getElementById('sidebar');

    // Track mouse movement
    resizer.addEventListener('mousedown', function(e) {
        e.preventDefault();
        document.addEventListener('mousemove', resize);
        document.addEventListener('mouseup', stopResize);
    });

    function resize(e) {
        // Calculate new width
        let newWidth = e.clientX;
        // Enforce basic constraints via JS logic (min 250, max 600)
        // CSS also enforces min-width/max-width, so this is just helper logic
        sidebar.style.width = newWidth + 'px';
    }

    function stopResize() {
        document.removeEventListener('mousemove', resize);
        document.removeEventListener('mouseup', stopResize);
    }
}

// KEYPRESS HANDLER
document.getElementById('msg-input').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
        if (e.ctrlKey || e.shiftKey) {
            e.preventDefault();
            const start = this.selectionStart;
            const end = this.selectionEnd;
            this.value = this.value.substring(0, start) + "\n" + this.value.substring(end);
            this.selectionStart = this.selectionEnd = start + 1;
        } else {
            e.preventDefault();
            sendMessage();
        }
    }
});

function initStarLogic() {
    const stars = document.querySelectorAll('.star');
    const container = document.querySelector('.star-container');
    if (!stars.length || !container) return;

    stars.forEach((star, index) => {
        star.addEventListener('mouseover', () => {
            stars.forEach((s, i) => {
                if (i <= index) s.classList.add('hovered');
                else s.classList.remove('hovered');
            });
        });
        star.onclick = () => submitRating(index + 1);
    });

    container.addEventListener('mouseleave', () => {
        stars.forEach(s => s.classList.remove('hovered'));
    });
}

// MAIN CHAT FUNCTION
async function sendMessage() {
    const input = document.getElementById('msg-input');
    const spinner = document.getElementById('loading-spinner');
    const chatContainer = document.getElementById('chat-container');
    const sendBtn = document.querySelector('#input-area button');

    const text = input.value.trim();
    if (!text) return;

    // LOCK BUTTON & INPUT
    sendBtn.disabled = true;
    sendBtn.style.opacity = "0.7";
    sendBtn.style.cursor = "not-allowed";

    input.disabled = true;

    addMessage(text, 'user-msg');
    input.value = '';

    spinner.style.display = 'block';
    chatContainer.appendChild(spinner);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const response = await fetch('/api/message', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: text})
        });
        const data = await response.json();

        spinner.style.display = 'none';

        if (data.reset_chat) {
            addMessage(data.bot_response, 'bot-msg');
            setTimeout(() => { resetChatUI(data.last_summary); }, 3000);
        } else {
            addMessage(data.bot_response, 'bot-msg');
        }

        if (data.recommendations && data.recommendations.length > 0) {
            renderCards(data.recommendations);
        }

        if (data.constraints) document.getElementById('constraints-box').innerText = data.constraints;
        if (data.user_summary) document.getElementById('summary-box').innerText = data.user_summary;
        if (data.system_msg) document.getElementById('system-box').innerText = data.system_msg;

    } catch (error) {
        console.error(error);
        spinner.style.display = 'none';
        addMessage("Sorry, connection error. Try again in a few seconds.", 'bot-msg');
    } finally {
        // UNLOCK EVERYTHING
        sendBtn.disabled = false;
        sendBtn.style.opacity = "1";
        sendBtn.style.cursor = "pointer";

        input.disabled = false;
        input.focus();
    }
}

async function openEditModal() {
    const overlay = document.getElementById('edit-overlay');
    overlay.style.display = 'flex';
    const res = await fetch('/api/get_profile');
    const data = await res.json();

    document.getElementById('edit-diet').value = (data.diet || []).join(', ');
    document.getElementById('edit-allergies').value = (data.allergies || []).join(', ');
    document.getElementById('edit-hated').value = (data.hated_ingredients || []).join(', ');
    document.getElementById('edit-texture').value = (data.texture_aversions || []).join(', ');
    document.getElementById('edit-nutrition').value = (data.nutrition_goals || []).join(', ');
    document.getElementById('edit-spice').value = data.spice_level || 'medium';

    if (data.budget && data.budget.max) {
        document.getElementById('edit-budget').value = data.budget.max;
    } else {
        document.getElementById('edit-budget').value = '';
    }
}

function closeEditModal() {
    document.getElementById('edit-overlay').style.display = 'none';
}

async function saveProfile() {
    const diet = document.getElementById('edit-diet').value.split(',').map(s=>s.trim()).filter(s=>s);
    const allergies = document.getElementById('edit-allergies').value.split(',').map(s=>s.trim()).filter(s=>s);
    const hated = document.getElementById('edit-hated').value.split(',').map(s=>s.trim()).filter(s=>s);
    const texture = document.getElementById('edit-texture').value.split(',').map(s=>s.trim()).filter(s=>s);
    const nutrition = document.getElementById('edit-nutrition').value.split(',').map(s=>s.trim()).filter(s=>s);
    const spice = document.getElementById('edit-spice').value;
    const budgetMax = document.getElementById('edit-budget').value;

    const payload = {
        diet: diet,
        allergies: allergies,
        hated_ingredients: hated,
        texture_aversions: texture,
        nutrition_goals: nutrition,
        spice_level: spice,
        budget: { max: budgetMax ? parseInt(budgetMax) : null, currency: "$" }
    };

    const res = await fetch('/api/get_profile');
    const existing = await res.json();
    const merged = { ...existing, ...payload };

    await fetch('/api/update_profile', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(merged)
    })
    .then(r => r.json())
    .then(data => {
        closeEditModal();
        document.getElementById('constraints-box').innerText = data.constraints;
        document.getElementById('summary-box').innerText = data.user_summary;
        document.getElementById('system-box').innerText = "✅ Profile Edited Manually";
    });
}

function placeOrder() {
    if (!currentDish) return;
    closeDetails();
    const dishId = currentDish.id || "D001";
    const cmd = `CMD:PLACE_ORDER|${dishId}|${currentDish.name}`;

    fetch('/api/message', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: cmd})
    })
    .then(r => r.json())
    .then(data => {
        addMessage(data.bot_response, 'bot-msg');
        document.getElementById('rating-overlay').style.display = 'flex';
        initStarLogic();
        if (data.system_msg) document.getElementById('system-box').innerText = data.system_msg;
    });
}

function submitRating(rating) {
    document.getElementById('rating-overlay').style.display = 'none';
    const spinner = document.getElementById('loading-spinner');
    const chatContainer = document.getElementById('chat-container');
    spinner.style.display = 'block';
    chatContainer.appendChild(spinner);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    sendMessageInternal(rating.toString());
}

async function sendMessageInternal(text) {
    const spinner = document.getElementById('loading-spinner');
    try {
        const response = await fetch('/api/message', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: text})
        });
        const data = await response.json();
        spinner.style.display = 'none';

        if (data.reset_chat) {
            resetChatUI(data.last_summary);
        } else {
            addMessage(data.bot_response, 'bot-msg');
        }

        if (data.constraints) document.getElementById('constraints-box').innerText = data.constraints;
        if (data.user_summary) document.getElementById('summary-box').innerText = data.user_summary;
        if (data.system_msg) document.getElementById('system-box').innerText = data.system_msg;

    } catch (error) {
        spinner.style.display = 'none';
        addMessage("Connection error.", 'bot-msg');
    }
}

function resetChatUI(lastSummary) {
    const chatContainer = document.getElementById('chat-container');
    const spinner = document.getElementById('loading-spinner');
    chatContainer.innerHTML = '';

    const displayText = lastSummary ? lastSummary : "Order completed.";

    const greeting = document.createElement('div');
    greeting.className = 'message bot-msg';
    greeting.innerHTML = `<strong>New Chat Started</strong><br>Previous: ${displayText}<br>How can I help you now?`;

    chatContainer.appendChild(greeting);
    spinner.style.display = 'none';
    chatContainer.appendChild(spinner);

    const sysBox = document.getElementById('system-box');
    if(sysBox) sysBox.innerText = "Ready.";
}

function addMessage(text, className) {
    const chatContainer = document.getElementById('chat-container');
    const div = document.createElement('div');
    div.classList.add('message', className);
    div.innerHTML = text.replace(/\n/g, '<br>');
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function renderCards(items) {
    const chatContainer = document.getElementById('chat-container');

    // Instruction Message
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', 'bot-msg');
    msgDiv.innerHTML = '👉 <span style="font-style:italic; color:#555;">Click to see details about the dish and the option to order.</span>';
    chatContainer.appendChild(msgDiv);

    const container = document.createElement('div');
    container.classList.add('cards-container');

    items.forEach(item => {
        const card = document.createElement('div');
        card.classList.add('card');
        card.onclick = () => showDetails(item);

        card.innerHTML = `
            <h4>${item.name}</h4>
            <div class="meta">
                <span>$${item.price}</span>
                <span>${item.restaurant}</span>
            </div>
            <div class="eta">🚚 ${item.eta || 'Soon'}</div>
        `;
        container.appendChild(card);
    });

    chatContainer.appendChild(container);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showDetails(item) {
    currentDish = item;
    const overlay = document.getElementById('details-overlay');
    const box = document.getElementById('details-box');

    document.getElementById('det-name').innerText = item.name;
    document.getElementById('det-rest').innerText = "Restaurant: " + item.restaurant;
    document.getElementById('det-price').innerText = `$${item.price}`;

    // Set Rating
    document.getElementById('det-rating').innerText = `⭐ ${item.rating || 'N/A'} Stars`;

    document.getElementById('det-eta').innerText = `Est: ${item.eta || 'N/A'}`;
    document.getElementById('det-ingredients').innerText = item.ingredients || "Not specified.";
    document.getElementById('det-explain').innerText = item.explanation;
    document.getElementById('det-desc').innerText = item.details || "";

    overlay.style.display = 'flex';
    setTimeout(() => { box.style.transform = 'scale(1)'; }, 10);
}

function closeDetails() {
    const overlay = document.getElementById('details-overlay');
    const box = document.getElementById('details-box');
    box.style.transform = 'scale(0.9)';
    setTimeout(() => { overlay.style.display = 'none'; }, 200);
}

document.getElementById('details-overlay').addEventListener('click', function(e) {
    if (e.target === this) closeDetails();
});