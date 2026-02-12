\documentclass[conference]{IEEEtran}

% ---------------- Packages ----------------
\usepackage{amsmath, amssymb}
\usepackage{algorithm}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{float}
\usepackage{caption}

% ---------------- Document ----------------
\begin{document}

\title{Vision-Language Guided Real-Time Virtual Try-On System}

\author{
\IEEEauthorblockN{Author Name}
\IEEEauthorblockA{Affiliation\\
Email}
}

\maketitle

\begin{abstract}
This paper presents a real-time virtual try-on system integrating
vision-language models with generative image synthesis.
\end{abstract}

\section{Introduction}
Introduction goes here.

\section{Methodology}

This work proposes a vision-language guided real-time virtual try-on framework that decouples body size understanding from garment rendering. The key idea is to leverage a Vision-Language Model (VLM) to infer structured anthropometric attributes from a single reference image, which are then used for deterministic garment selection prior to real-time virtual try-on synthesis. This separation reduces ambiguity, improves stability, and lowers computational overhead during live inference.

\subsection{System Architecture}

The system consists of three sequential modules: (i) body size inference via a Vision-Language Model, (ii) garment size matching using a structured clothing library, and (iii) real-time virtual try-on rendering using live camera input. The size estimation stage is executed once per user session, while the rendering pipeline operates continuously, enabling efficient real-time performance.

\begin{figure}[t]
    \centering
    \includegraphics[width=0.5\linewidth]{vton.png}
    \caption{Fig 1. System overview}
    \label{fig:system-overview}
\end{figure}

\subsection{Vision-Language-Based Body Size Inference}

Given a single RGB image of a user, the Vision-Language Model maps visual appearance to semantically meaningful body measurements. The implementation utilizes OpenRouter API with state-of-the-art multimodal models such as Claude 3.5 Sonnet, which implicitly encode visual priors learned from large-scale multimodal data, enabling coarse but robust estimation without explicit 3D reconstruction.

\subsubsection{Multimodal Transformer Architecture}

The underlying VLM architecture is based on vision transformers (ViT) combined with large language models (LLMs) through cross-attention mechanisms. Let $\mathcal{I} \in \mathbb{R}^{H \times W \times 3}$ denote the input RGB image, which is first encoded into a sequence of patch embeddings:

\begin{equation}
\mathbf{z}_i = \text{LayerNorm}(\mathbf{W}_p \cdot \text{Patch}(\mathcal{I})_i + \mathbf{b}_p), \quad i = 1, \ldots, N
\end{equation}

where $\mathbf{W}_p \in \mathbb{R}^{(P^2 \cdot 3) \times D}$ is the projection matrix, $P$ is the patch size, and $D$ is the embedding dimension. The text prompt $\mathcal{P}$ is encoded using a separate transformer encoder:

\begin{equation}
\mathbf{h}_t = \text{Transformer}_{\text{enc}}(\mathbf{E}_w \cdot \text{Token}(\mathcal{P})_t), \quad t = 1, \ldots, T
\end{equation}

where $\mathbf{E}_w \in \mathbb{R}^{V \times D}$ is the token embedding matrix with vocabulary size $V$. The vision and language modalities are fused through cross-attention layers:

\begin{equation}
\mathbf{c}_t = \sum_{i=1}^{N} \alpha_{t,i} \mathbf{z}_i, \quad \alpha_{t,i} = \frac{\exp(\mathbf{q}_t^\top \mathbf{k}_i / \sqrt{d_k})}{\sum_{j=1}^{N} \exp(\mathbf{q}_t^\top \mathbf{k}_j / \sqrt{d_k})}
\end{equation}

where $\mathbf{q}_t = \mathbf{W}_Q \mathbf{h}_t$, $\mathbf{k}_i = \mathbf{W}_K \mathbf{z}_i$, and $d_k$ is the key dimension.

\subsubsection{Structured Output Generation}

To enforce deterministic JSON output, the model employs constrained decoding techniques. Let $\mathcal{V}$ be the vocabulary and $\mathcal{S} \subset \mathcal{V}^*$ be the set of valid JSON sequences. The decoding objective is:

\begin{equation}
p(\mathbf{y} \mid \mathcal{I}, \mathcal{P}) = \prod_{t=1}^{|\mathbf{y}|} p(y_t \mid y_{<t}, \mathcal{I}, \mathcal{P}) \cdot \mathbb{I}[\mathbf{y}_{\leq t} \in \mathcal{S}]
\end{equation}

where $\mathbb{I}[\cdot]$ is an indicator function that enforces valid JSON syntax at each decoding step. The constrained decoding space prevents semantic drift and ensures reproducible outputs.

Formally, the VLM is modeled as a conditional mapping:
\begin{equation}
\mathbf{S}_u = f_{\text{VLM}}(I_u \mid P)
\end{equation}

where $I_u$ denotes the user reference image, $P$ is a constrained prompt, and $\mathbf{S}_u$ is a structured vector of anthropometric attributes.

\subsubsection{Fallback Estimation Mechanism}

To ensure system robustness in scenarios where the VLM fails to provide valid measurements (e.g., API errors, malformed responses, or model refusals), a deterministic fallback mechanism is implemented. This mechanism generates realistic measurements based on optional user-provided height information using anthropometric scaling factors:

\begin{align}
\text{chest} &= \text{height} \times 0.55 \times \mathcal{U}(0.9, 1.1) \\
\text{waist} &= \text{height} \times 0.48 \times \mathcal{U}(0.85, 1.15) \\
\text{hips} &= \text{height} \times 0.58 \times \mathcal{U}(0.9, 1.1) \\
\text{shoulder} &= \text{height} \times 0.25 \times \mathcal{U}(0.9, 1.1)
\end{align}

where $\mathcal{U}(a, b)$ denotes a uniform distribution over $[a, b]$, introducing reasonable variability while maintaining anatomical plausibility.

\subsection{Garment Size Matching}

Each garment in the database is represented by a canonical size vector derived from manufacturer specifications or metadata. The garment selection task is formulated as a distance minimization problem in measurement space:

\begin{equation}
g^* = \arg\min_{g_i \in \mathcal{G}} \; 
\left\| \mathbf{W} \odot (\mathbf{S}_u - \mathbf{S}_{g_i}) \right\|_1
\end{equation}

where $\mathbf{W}$ denotes a weight vector reflecting the relative importance of individual body dimensions, and $\odot$ represents element-wise multiplication. The $L_1$ norm is used to reduce sensitivity to outliers in individual measurements.

This explicit matching step ensures that only physically plausible garments are passed to the rendering stage.

\subsubsection{Size Category Classification}

For simplified garment filtering, measurements are mapped to discrete size categories (S, M, L, XL) using threshold-based classification on chest circumference:

\begin{equation}
\text{size} = 
\begin{cases}
\text{S} & \text{if } \text{chest} < 88 \\
\text{M} & \text{if } 88 \leq \text{chest} < 96 \\
\text{L} & \text{if } 96 \leq \text{chest} < 104 \\
\text{XL} & \text{if } \text{chest} \geq 104
\end{cases}
\end{equation}

This classification enables both exact size matching and approximate filtering for garments with standard size labels.

\subsection{Real-Time Virtual Try-On Rendering}

Once a garment is selected, the system enters real-time operation using live camera input. The implementation leverages the API4AI Cloud Virtual Try-On API, which provides end-to-end synthesis without requiring local computation of pose estimation or human parsing.

\subsubsection{API-Based Synthesis Pipeline}

The rendering process abstracts the complexity of pose-guided garment alignment and occlusion reasoning through a cloud-based service. Given a target frame $F_t$ and selected garment $g^*$, synthesis is modeled as:

\begin{equation}
\hat{F}_t = f_{\text{API4AI}}(F_t, g^*)
\end{equation}

where $f_{\text{API4AI}}$ represents a cloud-based virtual try-on model that internally handles pose estimation, human parsing, garment warping, and conditional image synthesis.

This API-based approach reduces client-side computational requirements while maintaining real-time performance through optimized server-side inference.

\subsection{AI-Powered Studio 3: Advanced Transformations}

Beyond traditional virtual try-on, the system incorporates a real-time AI transformation suite powered by the DecartAI Realtime API. This module extends functionality beyond garment overlay to enable creative video editing and style transformation.

\subsubsection{Multi-Mode Architecture}

Studio 3 operates in three distinct modes, each utilizing specialized generative models:

\begin{enumerate}
    \item \textbf{Mirage v2 (Style Transformation)}: Transforms video streams with artistic styles through style transfer techniques. The model accepts natural language prompts describing desired visual aesthetics, enabling effects such as "anime style," "cyberpunk city," or "studio Ghibli animation."

    \item \textbf{Lucy 2 (Video Editing)}: Enables object-level manipulation in real-time video. Users can add, modify, or remove objects through natural language commands such as "add a white T-shirt," "change shirt to white," or "remove jacket." This mode operates with top/bottom garment focus, making it ideal for clothing modifications.

    \item \textbf{Avatar Live (Talking Avatars)}: Generates lifelike animated avatars from static portrait images synchronized with audio input. The model learns to map audio features to facial articulations, creating synchronized lip movements and expressive animations suitable for virtual presenters and interactive agents.
\end{enumerate}

\subsubsection{Real-Time Inference Framework}

The DecartAI integration maintains WebSocket-based streaming connections for low-latency inference:

\begin{equation}
\hat{F}_t = f_{\text{DecartAI}}(F_t, P_t)
\end{equation}

where $P_t$ represents the user-provided prompt at time $t$, which can be dynamically updated during live sessions. The streaming architecture ensures frame-by-frame processing with minimal buffering, enabling interactive real-time feedback.

\subsection{End-to-End Pipeline Formulation}

The complete system can be viewed as a composition of modular functions:
\begin{equation}
\hat{F}_t = f_{\text{VTON}} \big( F_t,\; g^*,\; f_{\text{pose}}(F_t),\; f_{\text{seg}}(F_t) \big)
\end{equation}

This formulation highlights the decoupled nature of size inference and rendering, allowing each component to be independently improved or replaced.

\subsection{Potential Methods Explored}

\subsubsection{Pose-Guided Garment Alignment}

A pose estimation network extracts 2D skeletal keypoints that define the target body configuration. These keypoints guide the geometric transformation of the garment, ensuring alignment with the user's posture while preserving garment structure.

Let $\mathbf{K} = \{k_1, k_2, \ldots, k_J\}$ denote the set of $J$ detected keypoints, where $k_j \in \mathbb{R}^2$. The pose-guided warping can be formulated as:

\begin{equation}
\mathbf{T}(x) = \sum_{j=1}^{J} w_j(x) \cdot \mathcal{T}_j(x)
\end{equation}

where $\mathcal{T}_j$ is the transformation induced by keypoint $j$, and $w_j(x)$ is the blending weight at pixel location $x$, typically computed using a thin-plate spline (TPS) or moving least squares (MLS) deformation.

\subsubsection{Human Parsing and Occlusion Reasoning}

A human segmentation model generates pixel-level masks corresponding to body regions. These masks enable occlusion-aware synthesis, allowing correct handling of overlaps between garments, limbs, and background.

Let $\mathbf{M} = \{M_1, M_2, \ldots, M_R\}$ denote the set of $R$ segmentation masks, where $M_r \in \{0, 1\}^{H \times W}$. The mask-guided synthesis can be expressed as:

\begin{equation}
\hat{F}_t(x) = \sum_{r=1}^{R} M_r(x) \cdot G_r(x) + (1 - \sum_{r=1}^{R} M_r(x)) \cdot F_t(x)
\end{equation}

where $G_r(x)$ is the rendered appearance for region $r$, and $F_t(x)$ is the original frame.

The segmentation model is typically trained using cross-entropy loss:

\begin{equation}
\mathcal{L}_{\text{seg}} = -\frac{1}{HW} \sum_{x} \sum_{c=1}^{C} \mathbf{y}(x)_c \log \hat{\mathbf{y}}(x)_c
\end{equation}

where $\mathbf{y}$ is the ground-truth label map and $\hat{\mathbf{y}}$ is the predicted probability map over $C$ classes.

\subsubsection{Conditional Image Synthesis}

The final try-on image is produced by a conditional generative model that integrates the original frame, warped garment, and segmentation masks. Rather than explicitly modeling physical cloth dynamics, the generator learns appearance-consistent fusion through data-driven synthesis, which is sufficient for visually realistic try-on results.

Let $G_\theta$ denote the generator network with parameters $\theta$. The synthesis objective combines multiple loss terms:

\begin{align}
\mathcal{L}_{\text{total}} &= \lambda_{\text{rec}} \mathcal{L}_{\text{rec}} + \lambda_{\text{adv}} \mathcal{L}_{\text{adv}} + \lambda_{\text{perc}} \mathcal{L}_{\text{perc}} \\
\mathcal{L}_{\text{rec}} &= \frac{1}{HW} \sum_{x} \| \hat{F}_t(x) - F_t^{\text{gt}}(x) \|_1 \\
\mathcal{L}_{\text{adv}} &= \mathbb{E}_{x \sim p_{\text{data}}}[\log(1 - D_\phi(G_\theta(x)))] + \mathbb{E}_{z \sim p_z}[\log D_\phi(z)] \\
\mathcal{L}_{\text{perc}} &= \sum_{l \in \mathcal{L}} \| \Phi_l(\hat{F}_t) - \Phi_l(F_t^{\text{gt}}) \|_2^2
\end{align}

where $D_\phi$ is the discriminator network, $\Phi_l$ denotes features at layer $l$ of a pre-trained VGG network, and $\lambda$ terms balance the loss contributions.

\subsection{Design Rationale}

The proposed architecture avoids explicit 3D body reconstruction, camera calibration, or physics-based cloth simulation, which are computationally expensive and unstable in real-time settings. Instead, it leverages:
\begin{itemize}
    \item Learned priors from large-scale multimodal models (VLMs)
    \item Cloud-based inference for heavy computation (API4AI, DecartAI)
    \item Data-driven image synthesis through generative models
\end{itemize}

This hybrid approach strikes a balance between realism, robustness, and efficiency, making virtual try-on accessible through standard web browsers without requiring client-side GPU acceleration.

\subsection{Configuration Management}

The system implements a flexible API key management framework that allows runtime configuration of external service credentials. API keys for OpenRouter (size estimation), API4AI (virtual try-on), and DecartAI (Studio 3 transformations) can be configured through:
\begin{itemize}
    \item Environment variables for production deployments
    \item JSON-based configuration file for persistent settings
    \item Web-based settings interface for interactive configuration
\end{itemize}

This architecture enables seamless switching between service providers and facilitates deployment across different environments without code modifications.

\section{Experiments}
Experiments go here.

\section{Conclusion}
Conclusion goes here.

\bibliographystyle{IEEEtran}
\bibliography{references}

\end{document}
