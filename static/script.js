const chat = document.getElementById("chat");
const chatForm = document.getElementById("chatForm");
const imageInput = document.getElementById("imageInput");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const resetBtn = document.getElementById("resetBtn");
const fileLabel = document.getElementById("fileLabel");
const dropZone = document.getElementById("dropZone");
const dropHint = document.getElementById("dropHint");

function scrollChatToBottom() {
  chat.scrollTop = chat.scrollHeight;
}

function setSending(isSending) {
  sendBtn.disabled = isSending;
  sendBtn.textContent = isSending ? "Sending..." : "Send";
}

function setSelectedFile(file) {
  if (file) {
    fileLabel.textContent = file.name;
    dropHint.textContent = `Selected: ${file.name}`;
    dropZone.classList.add("has-file");
    return;
  }

  fileLabel.textContent = "No image selected";
  dropHint.textContent = "Drag and drop an image here, or click to attach";
  dropZone.classList.remove("has-file");
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read image file."));
    reader.readAsDataURL(file);
  });
}

function addMessage(role, { text = "", imageUrl = "" } = {}) {
  const item = document.createElement("div");
  item.className = `message ${role}`;

  const textEl = document.createElement("div");
  textEl.className = "message-text";
  textEl.textContent = text;
  item.appendChild(textEl);

  let imageEl = null;
  if (imageUrl) {
    imageEl = document.createElement("img");
    imageEl.className = "message-image";
    imageEl.src = imageUrl;
    imageEl.alt = "Uploaded image";
    imageEl.loading = "lazy";
    item.appendChild(imageEl);
  }

  chat.appendChild(item);
  scrollChatToBottom();
  return { item, textEl, imageEl };
}

async function typeTextSequence(textEl, fullText) {
  const tokens = fullText.split(/(\s+)/).filter((token) => token.length > 0);
  if (tokens.length === 0) {
    return;
  }

  const baseDelay = tokens.length > 180 ? 8 : 18;
  for (const token of tokens) {
    textEl.textContent += token;
    scrollChatToBottom();
    await new Promise((resolve) => setTimeout(resolve, baseDelay));
  }
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history", { method: "GET" });
    if (!response.ok) {
      throw new Error("Could not load history.");
    }

    const data = await response.json();
    const messages = Array.isArray(data.messages) ? data.messages : [];

    if (messages.length === 0) {
      addMessage("assistant", { text: "Welcome to ImageSeeker. Drop an image and ask anything." });
      return;
    }

    for (const message of messages) {
      const role = message.role === "assistant" ? "assistant" : "user";
      addMessage(role, {
        text: message.content || "",
        imageUrl: message.image_url || "",
      });
    }
  } catch (_) {
    addMessage("assistant", { text: "Welcome to ImageSeeker. Drop an image and ask anything." });
  }
}

function attachDroppedFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    addMessage("assistant", { text: "Please drop an image file (png, jpg, jpeg, webp, gif)." });
    return;
  }

  const dt = new DataTransfer();
  dt.items.add(file);
  imageInput.files = dt.files;
  setSelectedFile(file);
}

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    dropZone.classList.add("drag-over");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    event.stopPropagation();
    dropZone.classList.remove("drag-over");
  });
}

dropZone.addEventListener("drop", (event) => {
  const droppedFile = event.dataTransfer?.files?.[0];
  attachDroppedFile(droppedFile || null);
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();
  const imageFile = imageInput.files[0];

  if (!message && !imageFile) {
    addMessage("assistant", { text: "Please type a message or attach an image." });
    return;
  }

  const payload = new FormData();
  payload.append("message", message);

  let localImagePreview = "";
  if (imageFile) {
    payload.append("image", imageFile);
    localImagePreview = await fileToDataUrl(imageFile);
  }

  const userBubble = addMessage("user", {
    text: message || (localImagePreview ? "Image uploaded" : ""),
    imageUrl: localImagePreview,
  });

  messageInput.value = "";
  imageInput.value = "";
  setSelectedFile(null);

  setSending(true);
  const assistantBubble = addMessage("assistant", { text: "Analyzing..." });

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      body: payload,
    });

    let data = {};
    try {
      data = await response.json();
    } catch (_) {
      data = { error: "Server returned an invalid response." };
    }

    if (!response.ok) {
      assistantBubble.textEl.textContent = data.error || "Request failed.";
      return;
    }

    if (data.image_url && userBubble.imageEl) {
      userBubble.imageEl.src = data.image_url;
    }

    assistantBubble.textEl.textContent = "";
    await typeTextSequence(assistantBubble.textEl, data.reply || "No response received.");
  } catch (error) {
    assistantBubble.textEl.textContent = `Network error: ${error.message}`;
  } finally {
    setSending(false);
  }
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
    return;
  }

  event.preventDefault();
  if (!sendBtn.disabled) {
    chatForm.requestSubmit();
  }
});

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0] || null;
  setSelectedFile(file);
});

resetBtn.addEventListener("click", async () => {
  try {
    const response = await fetch("/api/reset", { method: "POST" });
    if (response.ok) {
      chat.innerHTML = "";
      addMessage("assistant", { text: "Conversation reset. Ready for a new image." });
    }
  } catch (_) {
    addMessage("assistant", { text: "Could not reset right now." });
  }
});

setSelectedFile(null);
loadHistory();
