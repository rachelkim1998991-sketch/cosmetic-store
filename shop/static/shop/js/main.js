let aiConversationHistory=[];

function formatAiText(text) {
    const escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    const withBold = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    const withBreaks = withBold.replace(/\n/g, '<br>');

    return withBreaks;
}

function getCsrfToken(){
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

function toggleFavorite(productId,button) {
    fetch(`/favorite/${productId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json',
        },
    })
    .then(response=>{
        if(response.status===403){
            window.location.href='/accounts/login/';
            return;
        }
        return response.json();
    })
    .then(data=>{
        if(!data) return;
        if(data.status==='added'){
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
}

function addToCart(productId,button){
    fetch(`/cart/add/${productId}/`,{
        method:'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json',
            },
    })
    .then(response=>{
        if(response.status===403){
            window.location.href='/accounts/login/';
            return;
        }
        return response.json();
    })
    .then(data=>{
        if(!data) return;
        const originalText=button.textContent;
        button.textContent="Qo'shildi ✓";
        setTimeout(()=> {
            button.textContent = originalText;
        },1200);
    });
}

function removeFromCart(itemId){
    fetch(`/cart/remove/${itemId}/`,{
        method:'POST',
        headers:{
            'X-CSRFToken':getCsrfToken(),
            'Content-Type':'application/json',
            },
    })
    .then(response=>response.json())
    .then(data=>{
        if (data.status === 'removed') {
            location.reload();
        }
    })
}


function toggleAiChat(){
    const box=document.getElementById('aiChatBox');
    box.classList.toggle('open');
}

function sendAiMessage() {
    const input = document.getElementById('aiChatInput');
    const message = input.value.trim();
    if (!message) return;

    const messagesDiv = document.getElementById('aiChatMessages');

    const userMsg = document.createElement('div');
    userMsg.className = 'ai-message ai-message-user';
    userMsg.textContent = message;
    messagesDiv.appendChild(userMsg);

    aiConversationHistory.push({ role: 'user', text: message });

    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'ai-message ai-message-bot';
    loadingMsg.textContent = 'Yozmoqda...';
    loadingMsg.id = 'aiLoadingMsg';
    messagesDiv.appendChild(loadingMsg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    fetch('/ai-assistant/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            history: aiConversationHistory.slice(0, -1)
        }),
    })
    .then(response => response.json())
    .then(data => {
        const loading = document.getElementById('aiLoadingMsg');
        if (loading) loading.remove();

        const replyText = data.reply || data.error || 'Xatolik yuz berdi.';

        const botMsg = document.createElement('div');
        botMsg.className = 'ai-message ai-message-bot';
        botMsg.innerHTML = formatAiText(replyText);
        messagesDiv.appendChild(botMsg);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        aiConversationHistory.push({ role: 'assistant', text: replyText });
    })
    .catch(() => {
        const loading = document.getElementById('aiLoadingMsg');
        if (loading) loading.remove();
        const errorMsg = document.createElement('div');
        errorMsg.className = 'ai-message ai-message-bot';
        errorMsg.textContent = 'Server bilan bog\'lanishda xatolik';
        messagesDiv.appendChild(errorMsg);
    });
}

document.addEventListener('DOMContentLoaded',function(){
    const input=document.getElementById('aiChatInput');
    if (input) {
        input.addEventListener('keypress',function(e) {
            if (e.key==='Enter'){
                sendAiMessage();
            }
        });
    }
});

let currentBanner = 0;
let bannerAutoTimer = null;

function changeBanner(direction) {
    const track = document.getElementById('bannerTrack');
    if (!track) return;
    const slides = track.children.length;
    currentBanner = (currentBanner + direction + slides) % slides;
    track.style.transform = `translateX(-${currentBanner * 100}%)`;

    resetBannerAutoPlay();
}

function startBannerAutoPlay() {
    const track = document.getElementById('bannerTrack');
    if (!track || track.children.length <= 1) return;

    bannerAutoTimer = setInterval(() => {
        changeBannerAuto();
    }, 5000);
}

function changeBannerAuto() {
    const track = document.getElementById('bannerTrack');
    if (!track) return;
    const slides = track.children.length;
    currentBanner = (currentBanner + 1) % slides;
    track.style.transform = `translateX(-${currentBanner * 100}%)`;
}

function resetBannerAutoPlay() {
    if (bannerAutoTimer) {
        clearInterval(bannerAutoTimer);
    }
    startBannerAutoPlay();
}

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('bannerTrack')) {
        startBannerAutoPlay();
    }
});

let galleryImages = [];
let currentImageIndex = 0;

function initGallery() {
    const thumbs = document.querySelectorAll('.thumbnail');
    galleryImages = Array.from(thumbs).map(t => t.src);
    currentImageIndex = 0;
}

function changeMainImage(thumbEl, imageUrl) {
    const mainImg = document.getElementById('mainProductImage');
    if (mainImg && mainImg.tagName === 'IMG') {
        mainImg.src = imageUrl;
    }

    const thumbs = document.querySelectorAll('.thumbnail');
    thumbs.forEach((t, i) => {
        t.classList.remove('active');
        if (t === thumbEl) {
            currentImageIndex = i;
        }
    });
    thumbEl.classList.add('active');
}

function scrollThumbnails(direction) {
    if (galleryImages.length === 0) return;

    currentImageIndex = (currentImageIndex + direction + galleryImages.length) % galleryImages.length;

    const mainImg = document.getElementById('mainProductImage');
    if (mainImg && mainImg.tagName === 'IMG') {
        mainImg.src = galleryImages[currentImageIndex];
    }

    const thumbs = document.querySelectorAll('.thumbnail');
    thumbs.forEach((t, i) => {
        t.classList.toggle('active', i === currentImageIndex);
    });

    const activeThumb = thumbs[currentImageIndex];
    if (activeThumb) {
        activeThumb.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('mainProductImage')) {
        initGallery();
    }
});

let searchDebounceTimer;

function handleSearchInput(value) {
    clearTimeout(searchDebounceTimer);
    const box = document.getElementById('searchSuggestions');

    if (value.trim().length < 2) {
        box.innerHTML = '';
        box.classList.remove('active');
        return;
    }

    searchDebounceTimer = setTimeout(() => {
        fetch(`/search-suggestions/?q=${encodeURIComponent(value)}`)
            .then(response => response.json())
            .then(data => {
                renderSuggestions(data.results);
            });
    }, 300);
}

function renderSuggestions(results) {
    const box = document.getElementById('searchSuggestions');

    if (results.length === 0) {
        box.innerHTML = '<div class="suggestion-empty">Mos mahsulot topilmadi</div>';
        box.classList.add('active');
        return;
    }

    box.innerHTML = results.map(r => `
        <a href="${r.url}" class="suggestion-item">
            ${r.image ? `<img src="${r.image}" alt="${r.name}">` : '<div class="suggestion-img-placeholder"></div>'}
            <div class="suggestion-info">
                <span class="suggestion-name">${r.name}</span>
                <span class="suggestion-brand">${r.brand}</span>
            </div>
        </a>
    `).join('');

    box.classList.add('active');
}

document.addEventListener('click', function(e) {
    const searchBox = document.querySelector('.search-box');
    const suggestions = document.getElementById('searchSuggestions');
    if (searchBox && !searchBox.contains(e.target)) {
        suggestions.classList.remove('active');
    }
});

