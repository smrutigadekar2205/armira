
Video Editing
Edit live video streams in realtime with precise modifications. Add objects, change elements, or modify appearances in any live video feed with minimal latency. The Video Editing Realtime API takes a video stream and editing instructions, then generates a modified version of the video with your requested changes applied in realtime.
​
Model Specifications
The model processes video with these specifications:

    Frame Rate: 25 FPS
    Resolution: 1280x704 (16:9 aspect ratio)

​
Realtime API
The realtime API uses WebRTC for low-latency video editing. Clients establish a connection with our inference server, stream video with editing instructions, and receive a modified video stream in return. The connection remains active as long as the input video stream continues, allowing you to apply different edits on-the-fly to modify the output video dynamically.
​
Installation

npm install @decartai/sdk

​
Basic Usage

import { createDecartClient, models } from "@decartai/sdk";

const model = models.realtime("lucy_v2v_720p_rt");

// Get user's camera stream with model specifications
const stream = await navigator.mediaDevices.getUserMedia({
  audio: true,
  video: {
    frameRate: model.fps,
    width: model.width,
    height: model.height,
  }
});

// Create a client
const client = createDecartClient({
  apiKey: "your-api-key-here"
});

// Connect and edit the video stream
const realtimeClient = await client.realtime.connect(stream, {
  model,
  onRemoteStream: (editedStream) => {
    // Display the edited video
    const videoElement = document.querySelector("#video-output");
    videoElement.srcObject = editedStream;
  }
});

// Apply different edits on the fly
realtimeClient.setPrompt("Change the person's shirt to red");

// Disconnect when done
realtimeClient.disconnect();

​
Advanced Features
​
Character Reference
Use a reference image to transform yourself into a different character, the model will use this image as a visual reference for how you should appear.
Character reference only works with the lucy_2_rt model.

import { createDecartClient, models } from "@decartai/sdk";

// Use Lucy 2 for character reference support
const model = models.realtime("lucy_2_rt");

const stream = await navigator.mediaDevices.getUserMedia({
  audio: true,
  video: {
    frameRate: model.fps,
    width: model.width,
    height: model.height,
  }
});

const client = createDecartClient({
  apiKey: "your-api-key-here"
});

const realtimeClient = await client.realtime.connect(stream, {
  model,
  onRemoteStream: (editedStream) => {
    videoElement.srcObject = editedStream;
  }
});

// Set a character reference image
const fileInput = document.querySelector('input[type="file"]');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (file) {
    await realtimeClient.setImage(file);
  }
});

// Or set from a URL
await realtimeClient.setImage('https://example.com/character-reference.jpg');

Supported formats: JPEG, PNG, WebP
Character reference works great for transforming yourself into a specific character or person, or to add accessories, change outfits, or modify the scene.
​
Dynamic Video Editing

// Add objects to the scene
realtimeClient.setPrompt("Add a bird flying overhead");

// Modify existing elements
realtimeClient.setPrompt("Change the car color to blue");

// Remove objects from the scene
realtimeClient.setPrompt("Remove the tree from the background");

// Change appearances
realtimeClient.setPrompt("Make the person's hair blonde");

​
Connection State Management

import { createDecartClient, type DecartSDKError } from "@decartai/sdk";

const realtimeClient = await client.realtime.connect(stream, {
  model,
  onRemoteStream: (editedStream) => {
    videoElement.srcObject = editedStream;
  }
});

// Monitor connection state
realtimeClient.on("connectionChange", (state) => {
  console.log(`Connection: ${state}`); // "connecting" | "connected" | "disconnected"
  
  if (state === "connected") {
    document.getElementById("status").textContent = "Live Editing";
  } else if (state === "disconnected") {
    document.getElementById("status").textContent = "Disconnected";
  }
});

// Handle errors
realtimeClient.on("error", (error: DecartSDKError) => {
  console.error("SDK error:", error.code, error.message);
});

// Check connection synchronously
const isConnected = realtimeClient.isConnected();
const currentState = realtimeClient.getConnectionState();

​
Complete Example with Error Handling

import { createDecartClient, models, type DecartSDKError } from "@decartai/sdk";

async function setupVideoEditing() {
  try {
    const model = models.realtime("lucy_v2v_720p_rt");
    
    // Get camera with optimal settings
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: {
        frameRate: model.fps,
        width: model.width,
        height: model.height,
      }
    });

    const client = createDecartClient({
      apiKey: process.env.DECART_API_KEY
    });

    const realtimeClient = await client.realtime.connect(stream, {
      model,
      onRemoteStream: (editedStream) => {
        const videoElement = document.getElementById("output-video");
        videoElement.srcObject = editedStream;
      }
    });

    // Set up event handlers
    realtimeClient.on("connectionChange", (state) => {
      updateUIStatus(state);
    });

    realtimeClient.on("error", (error) => {
      console.error("Error:", error);
      showErrorMessage(error.message);
    });

    // Editing controls
    document.getElementById("add-dog").addEventListener("click", () => {
      realtimeClient.setPrompt("Add a small dog running around");
    });

    document.getElementById("change-hair").addEventListener("click", () => {
      realtimeClient.setPrompt("Change the person's hair to curly brown hair");
    });

    document.getElementById("add-sunglasses").addEventListener("click", () => {
      realtimeClient.setPrompt("Add stylish sunglasses to the person");
    });

    // Cleanup on page unload
    window.addEventListener("beforeunload", () => {
      realtimeClient.disconnect();
    });

    return realtimeClient;
  } catch (error) {
    console.error("Setup failed:", error);
    throw error;
  }
}

​
WebSocket + WebRTC (Vanilla)
For direct WebSocket communication without the SDK:

<!DOCTYPE html>
<html>
<head>
  <title>Video Editing - WebRTC</title>
</head>
<body>
  <!-- Local and edited video streams -->
  <video id="localVideo" autoplay muted playsinline width="45%"></video>
  <video id="remoteVideo" autoplay playsinline width="45%"></video>
  <br>
  
  <!-- Controls -->
  <button id="startBtn">Start</button>
  <input id="promptInput" placeholder="Enter editing instruction...">
  <button id="sendBtn">Apply Edit</button>
  
  <!-- Quick edit buttons -->
  <br><br>
  <button onclick="quickEdit('Add a small dog in the background')">Add Dog</button>
  <button onclick="quickEdit('Change the shirt color to blue')">Blue Shirt</button>
  <button onclick="quickEdit('Add sunglasses to the person')">Add Sunglasses</button>

  <script>
    // WebSocket connection with API key and model
    const ws = new WebSocket('wss://api3.decart.ai/v1/stream?api_key=YOUR_API_KEY&model=lucy_v2v_720p_rt');
    let peerConnection;

    // Handle server messages
    ws.onmessage = async (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'answer' && peerConnection) {
        await peerConnection.setRemoteDescription({
          type: 'answer', 
          sdp: message.sdp
        });
      }
    };

    // Start WebRTC connection
    async function startConnection() {
      if (ws.readyState !== WebSocket.OPEN) return;

      // Create peer connection
      peerConnection = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      });

      // Send ICE candidates to server
      peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
          ws.send(JSON.stringify({
            type: 'ice-candidate',
            candidate: event.candidate
          }));
        }
      };

      // Receive edited video stream
      peerConnection.ontrack = (event) => {
        document.getElementById('remoteVideo').srcObject = event.streams[0];
      };

      // Get user camera with optimal settings
      const localStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 704 },
          frameRate: { ideal: 25 }
        },
        audio: false
      });

      // Display local video
      document.getElementById('localVideo').srcObject = localStream;
      
      // Add tracks to peer connection
      localStream.getTracks().forEach(track => {
        peerConnection.addTrack(track, localStream);
      });

      // Create and send offer
      const offer = await peerConnection.createOffer();
      await peerConnection.setLocalDescription(offer);
      
      ws.send(JSON.stringify({
        type: 'offer',
        sdp: offer.sdp
      }));
    }

    // Send editing instruction
    function sendPrompt() {
      const promptInput = document.getElementById('promptInput');
      const prompt = promptInput.value.trim();
      
      if (prompt && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'prompt',
          prompt: prompt
        }));
      }
    }

    // Quick edit function
    function quickEdit(prompt) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'prompt',
          prompt: prompt
        }));
      }
    }

    // Event listeners
    document.getElementById('startBtn').onclick = startConnection;
    document.getElementById('sendBtn').onclick = sendPrompt;
    document.getElementById('promptInput').onkeypress = (e) => {
      if (e.key === 'Enter') sendPrompt();
    };
  </script>
</body>
</html>
