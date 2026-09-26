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

function sendAiMessage(){
    const input=document.getElementById('aiChatInput');
    const message=input.value.trim();
    if(!message) return;

    const messagesDiv=document.getElementById('aiChatMessages');

    const userMsg=document.createElement('div');
    userMsg.className='ai-message ai-message-user';
    userMsg.textContent=message;
    messagesDiv.appendChild(userMsg);

    input.value='';
    messagesDiv.scrollTop=messagesDiv.scrollHeight;

    const loadingMsg=document.createElement('div');
    loadingMsg.className='ai-message ai-message-bot';
    loadingMsg.textContent='Yozmoqda...';
    loadingMsg.id='aiLoadingMsg';
    messagesDiv.appendChild(loadingMsg);
    messagesDiv.scrollTop=messagesDiv.scrollHeight;

    fetch('/ai-assistant/',{
        method:'POST',
        headers:{
            'X-CSRFToken':getCsrfToken(),
            'Content-Type':'application/json',
        },
        body:JSON.stringify({message:message}),
    })
    .then(response=>response.json())
    .then(data=>{
        const loading=document.getElementById('aiLoadingMsg');
        if (loading) loading.remove();

        const botMsg=document.createElement('div');
        botMsg.className='ai-message ai-message-bot';
        botMsg.textContent=data.reply || data.error || 'Xatolik yuz berdi.';
        messagesDiv.appendChild(botMsg);
        messagesDiv.scrollTop=messagesDiv.scrollHeight;
        })

        .catch(()=>{
            const loading=document.getElementById('aiLoadingMsg');
            if (loading) loading.remove();
            const errorMsg=document.createElement('div');
            errorMsg.className='ai-message ai-message-bot';
            errorMsg.textContent='Server bilan bog\'lanishda xatolik';
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