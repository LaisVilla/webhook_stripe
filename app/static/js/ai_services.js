document.addEventListener('DOMContentLoaded', function () {
    // Elementos do DOM
    const aiForm = document.getElementById('aiForm');
    const userInput = document.getElementById('user_input');
    const submitButton = document.getElementById('submitButton');
    const buttonText = document.getElementById('buttonText');
    const loadingIcon = document.getElementById('loadingIcon');
    const loadingState = document.getElementById('loadingState');
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    const responseSection = document.getElementById('responseSection');
    const aiResponse = document.getElementById('aiResponse');
    const timestamp = document.getElementById('timestamp');
    const chatHistory = document.getElementById('chatHistory');

    // Elementos das estatísticas
    const remainingRequestsElement = document.getElementById('remaining-requests');
    const usageProgressElement = document.getElementById('usage-progress');
    const totalRequestsElement = document.querySelector('.total-requests');
    const totalTokensElement = document.querySelector('.total-tokens');
    const lastUpdateElement = document.querySelector('.last-update');

    // Função para atualizar a barra de progresso
    function updateProgressBar(percentage) {
        if (usageProgressElement) {
            const limitedPercentage = Math.min(Math.max(percentage, 0), 100);
            usageProgressElement.style.width = `${limitedPercentage}%`;
            usageProgressElement.classList.remove('bg-green-500', 'bg-yellow-500', 'bg-red-500');
            if (limitedPercentage < 50) {
                usageProgressElement.classList.add('bg-green-500');
            } else if (limitedPercentage < 80) {
                usageProgressElement.classList.add('bg-yellow-500');
            } else {
                usageProgressElement.classList.add('bg-red-500');
            }
        }
    }

    // Função para atualizar estatísticas do usuário
    function updateAIStats() {
        fetch('/api/user/ai-stats')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    if (remainingRequestsElement) {
                        remainingRequestsElement.textContent = data.data.remaining_requests;
                    }
                    updateProgressBar(data.data.usage_percentage);
                    if (totalRequestsElement) {
                        totalRequestsElement.textContent = data.data.total_requests;
                    }
                    if (totalTokensElement) {
                        const tokenCount = (data.data.total_tokens / 1000).toFixed(1);
                        totalTokensElement.textContent = `${tokenCount}K`;
                    }
                    if (lastUpdateElement) {
                        lastUpdateElement.textContent = data.data.timestamp;
                    }
                }
            })
            .catch(error => {
                console.error('Erro ao atualizar estatísticas:', error);
            });
    }

    // Event Listener para o formulário
    aiForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const userMessage = userInput.value.trim();

        // Validar input
        if (!userMessage) {
            showError('Por favor, digite uma mensagem.');
            return;
        }

        // Adicionar mensagem do usuário ao histórico
        addMessageToHistory(userMessage, true);

        // Mostrar estado de loading
        setLoadingState(true);
        hideError();

        try {
            const response = await fetch('/ai-services', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    input: userMessage,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erro ao processar sua requisição');
            }

            // Adicionar resposta do bot ao histórico
            addMessageToHistory(data.response, false, data.timestamp);

            // Limpar input
            userInput.value = '';

            // Atualizar estatísticas após resposta bem-sucedida
            updateAIStats();

        } catch (error) {
            console.error('Erro:', error);
            showError(error.message || 'Ocorreu um erro ao processar sua requisição');
        } finally {
            setLoadingState(false);
            chatHistory.scrollTop = chatHistory.scrollHeight; // Rolagem automática
        }
    });

    // Função para controlar o estado de loading
    function setLoadingState(isLoading) {
        if (isLoading) {
            buttonText.classList.add('hidden');
            loadingIcon.classList.remove('hidden');
            loadingState.classList.remove('hidden');
            submitButton.disabled = true;
        } else {
            buttonText.classList.remove('hidden');
            loadingIcon.classList.add('hidden');
            loadingState.classList.add('hidden');
            submitButton.disabled = false;
        }
    }

    // Função para mostrar erro
    function showError(message) {
        errorText.textContent = message;
        errorMessage.classList.remove('hidden');
        setTimeout(() => {
            errorMessage.classList.add('hidden');
        }, 5000);
    }

    // Função para esconder erro
    function hideError() {
        errorMessage.classList.add('hidden');
    }

    // Função para copiar resposta para o clipboard
    window.copyToClipboard = function (button) {
        const message = button.getAttribute('data-message');
        navigator.clipboard
            .writeText(message)
            .then(() => {
                const originalText = button.innerHTML;
                button.innerHTML = '<i class="lucide lucide-check h-4 w-4"></i><span>Copiado!</span>';
                setTimeout(() => {
                    button.innerHTML = originalText;
                }, 2000);
            })
            .catch(err => {
                console.error('Erro ao copiar texto:', err);
                showError('Erro ao copiar texto');
            });
    };

    // Função para adicionar mensagem ao histórico
    function addMessageToHistory(content, isUser = false, customTimestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message animate-fade-in';

        const currentTime = customTimestamp || new Date().toLocaleString();

        messageDiv.innerHTML = `
            <div class="flex items-start space-x-3 ${isUser ? 'justify-end' : ''}">
                <div class="flex-shrink-0">
                    <div class="h-8 w-8 rounded-lg bg-gradient-to-r ${
                        isUser ? 'from-tertiary to-secondary' : 'from-primary to-secondary'
                    } flex items-center justify-center">
                        <i class="lucide ${
                            isUser ? 'lucide-user' : 'lucide-bot'
                        } text-white h-5 w-5"></i>
                    </div>
                </div>
                <div class="flex-1">
                    <div class="bg-surface/30 rounded-xl p-4 ${
                        isUser ? 'bg-primary/20 text-right' : ''
                    }">
                        <p class="text-gray-300 whitespace-pre-wrap">${content}</p>
                    </div>
                    <div class="mt-2 flex items-center justify-between">
                        <span class="text-xs text-gray-500">${currentTime}</span>
                        ${
                            !isUser
                                ? ` 
                            <button 
                                onclick="copyToClipboard(this)"
                                class="btn-secondary inline-flex items-center gap-2 text-xs py-1 px-3"
                                data-message="${content.replace(/"/g, '&quot;')}">
                                <i class="lucide lucide-copy h-4 w-4"></i>
                                <span>Copiar</span>
                            </button>
                        `
                                : ''
                        }
                    </div>
                </div>
            </div>
        `;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight; // Rolagem automática
    }

    // Inicializar estatísticas quando a página carregar
    updateAIStats();

    // Atualizar estatísticas a cada 5 minutos
    setInterval(updateAIStats, 300000);
});
