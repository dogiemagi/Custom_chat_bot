document.addEventListener("DOMContentLoaded", () => {
    const uploadForm = document.getElementById("upload-form");
    const fileInput = document.getElementById("file-input");
    const uploadStatus = document.getElementById("upload-status");

    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatBox = document.getElementById("chat-box");
    const sendButton = chatForm.querySelector("button");

    // --- File Upload Logic ---
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            showStatus("Please select a file to upload.", "error");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        showStatus("Uploading and processing...", "processing");
        sendButton.disabled = true;
        userInput.disabled = true;

        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (response.ok) {
                showStatus(data.success, "success");
                // Enable chat input after successful upload
                userInput.disabled = false;
                sendButton.disabled = false;
                addMessage("Your document has been processed. You can now ask questions.", "bot-message");
            } else {
                throw new Error(data.error || "An unknown error occurred.");
            }
        } catch (error) {
            // Provide a more detailed error message for the user
            let errorMessage = `Error: ${error.message}`;
            if (error.message.toLowerCase().includes("failed to process the file")) {
                errorMessage = "Error: Failed to process the file.\n\nThis is likely a server-side issue. Common causes include:\n- An unsupported or corrupted file.\n- Missing backend dependencies (e.g., PyPDF).\n- Problems downloading the embedding model.\n\nPlease check the backend server logs for the specific error.";
            }
            showStatus(errorMessage, "error");
        }
    });

    function showStatus(message, type) {
        // Use innerText to correctly render newline characters in the error message
        uploadStatus.innerText = message;
        uploadStatus.className = type; // 'success' or 'error'
    }

    // --- Chat Logic ---
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const userMessage = userInput.value.trim();
        if (!userMessage) return;

        addMessage(userMessage, "user-message");
        userInput.value = "";
        
        const loadingMessage = addMessage("Thinking...", "bot-message loading");

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMessage }),
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || "Network response was not ok.");
            }

            const data = await response.json();
            loadingMessage.querySelector('p').textContent = data.response;
            loadingMessage.classList.remove('loading');
            
        } catch (error) {
            console.error("Error:", error);
            loadingMessage.querySelector('p').textContent = `Sorry, an error occurred: ${error.message}`;
            loadingMessage.classList.remove('loading');
        }
    });

    function addMessage(text, className) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message ${className}`;
        
        const messageP = document.createElement("p");
        messageP.textContent = text;
        
        messageDiv.appendChild(messageP);
        chatBox.appendChild(messageDiv);
        
        chatBox.scrollTop = chatBox.scrollHeight;
        return messageDiv;
    }
});

