document.addEventListener('DOMContentLoaded', () => {
    const questionEl = document.getElementById('question');
    const answersEl = document.getElementById('answers');
    const qaContainer = document.getElementById('qa-container');
    const promptContainer = document.getElementById('prompt-container');
    const promptEl = document.getElementById('prompt');
    const copyButton = document.getElementById('copy-button');

    let userTags = new Set();
    let userPath = [];
    let askedQuestions = new Set();

    const questions = {
        'start': {
            text: "What is the primary goal of your application?",
            answers: [
                { text: "To connect people", tags: ['social', 'community'], pros: "Builds a user base, potential for network effects.", cons: "Requires moderation, can be hard to get initial traction." },
                { text: "To solve a specific problem", tags: ['utility', 'productivity'], pros: "Clear value proposition, easier to market.", cons: "Can be niche, may have existing competitors." },
                { text: "To entertain or inspire", tags: ['entertainment', 'creative'], pros: "High potential for virality, can be very engaging.", cons: "Monetization can be tricky, trends change quickly." },
                { text: "To showcase a portfolio or project", tags: ['showcase', 'personal'], pros: "Full creative control, great for personal branding.", cons: "Limited audience, requires self-promotion." }
            ]
        },
        'tech_stack': {
            text: "What's the vibe for the tech stack?",
            answers: [
                { text: "Modern & Fast (e.g., React/Svelte)", tags: ['frontend-heavy', 'modern-js'], pros: "Excellent performance, great developer experience.", cons: "Can be complex, build tools required." },
                { text: "Simple & Classic (e.g., HTML/CSS/Vanilla JS)", tags: ['simple', 'no-framework'], pros: "Easy to learn, no dependencies.", cons: "Can get messy for larger projects, less powerful." },
                { text: "All-in-One (e.g., Rails/Django)", tags: ['full-stack-framework', 'backend-heavy'], pros: "Convention over configuration, rapid development.", cons: "Less frontend flexibility, can be monolithic." },
                { text: "Mobile Native (e.g., Swift/Kotlin)", tags: ['mobile', 'native'], pros: "Best performance and device integration.", cons: "Separate codebases for iOS/Android, more expensive." }
            ]
        },
        'social_platform': {
            condition: 'social',
            text: "What kind of social platform are you imagining?",
            answers: [
                { text: "A community forum or discussion board", tags: ['forum', 'discussion'], pros: "Fosters deep conversations and community.", cons: "Can be slow to grow, requires active moderation." },
                { text: "A private messaging or chat app", tags: ['messaging', 'chat'], pros: "High user engagement, encourages direct connection.", cons: "Privacy and security are critical and complex." },
                { text: "A media sharing platform (photos, videos)", tags: ['media-sharing', 'content-creation'], pros: "Very engaging, high potential for user-generated content.", cons: "Requires significant storage and bandwidth." },
                { text: "A location-based connection app", tags: ['location-based', 'networking'], pros: "Facilitates real-world connections, can be very sticky.", cons: "Privacy concerns, needs a critical mass of users in an area." }
            ]
        },
        'utility_type': {
            condition: 'utility',
            text: "What kind of utility does your app provide?",
            answers: [
                { text: "Data management or organization", tags: ['data-tool', 'organization'], pros: "High value for users, can become essential.", cons: "Can be complex to build, data security is paramount." },
                { text: "A daily planner or to-do list", tags: ['planning', 'task-manager'], pros: "Large potential user base, clear purpose.", cons: "Very crowded market with established players." },
                { text: "A specialized calculator or converter", tags: ['calculator', 'single-purpose'], pros: "Simple to build, solves a clear need.", cons: "Limited functionality, may not retain users." },
                { text: "A note-taking or documentation app", tags: ['notes', 'writing-tool'], pros: "Can be very sticky, users store valuable data.", cons: "High competition, features like syncing can be complex." }
            ]
        }
    };

    // Function to start the wizard
    function start() {
        showQuestion('start');
    }

    // Function to display a question
    function showQuestion(questionId) {
        askedQuestions.add(questionId);
        const questionData = questions[questionId];

        if (!questionData) {
            generatePrompt();
            return;
        }

        questionEl.textContent = questionData.text;
        answersEl.innerHTML = '';

        questionData.answers.forEach(answer => {
            const li = document.createElement('li');
            li.textContent = answer.text;
            li.dataset.tags = JSON.stringify(answer.tags);
            li.addEventListener('click', () => selectAnswer(answer));
            answersEl.appendChild(li);
        });

        // Add the explanation option
        const explanationLi = document.createElement('li');
        explanationLi.textContent = "Explain these options and their pros/cons.";
        explanationLi.classList.add('explanation');
        explanationLi.addEventListener('click', () => showExplanation(questionData.answers));
        answersEl.appendChild(explanationLi);
    }

    // Function to handle answer selection
    function selectAnswer(answer) {
        answer.tags.forEach(tag => userTags.add(tag));
        userPath.push(answer.text);

        const nextQuestionId = getNextQuestionId();
        showQuestion(nextQuestionId);
    }

    // Function to determine the next question based on tags
    function getNextQuestionId() {
        // Find questions whose conditions are met by userTags and haven't been asked
        const conditionalQuestions = Object.keys(questions).filter(id => {
            const question = questions[id];
            return !askedQuestions.has(id) && question.condition && userTags.has(question.condition);
        });

        if (conditionalQuestions.length > 0) {
            return conditionalQuestions[0];
        }

        // Fallback to generic questions that haven't been asked
        const genericQuestions = Object.keys(questions).filter(id => {
            return !askedQuestions.has(id) && !questions[id].condition;
        });

        if (genericQuestions.length > 0) {
            return genericQuestions[0];
        }

        return null; // No more questions
    }

    // Function to show explanations
    function showExplanation(answers) {
        let explanation = "Here's a breakdown of the choices:\n\n";
        answers.forEach(answer => {
            explanation += `*${answer.text}*:\n`;
            explanation += `  - **Pros:** ${answer.pros}\n`;
            explanation += `  - **Cons:** ${answer.cons}\n\n`;
        });
        alert(explanation);
    }

    // Function to generate and display the final prompt
    function generatePrompt() {
        qaContainer.style.display = 'none';
        promptContainer.style.display = 'block';

        // --- Masterfully Crafted Prompt Generation ---

        // Determine primary goal from tags
        let goal = "a unique application";
        if (userTags.has('social')) goal = "a social platform for connecting people";
        else if (userTags.has('utility')) goal = "a tool to solve a specific problem";
        else if (userTags.has('entertainment')) goal = "an entertaining and inspiring experience";
        else if (userTags.has('showcase')) goal = "a personal portfolio or project showcase";

        // Determine tech vibe from tags
        let techVibe = "a suitable modern stack";
        if (userTags.has('frontend-heavy')) techVibe = "a modern, frontend-heavy stack (like React or Svelte)";
        else if (userTags.has('simple')) techVibe = "a simple and classic stack (HTML, CSS, Vanilla JS)";
        else if (userTags.has('full-stack-framework')) techVibe = "an all-in-one framework (like Rails or Django)";
        else if (userTags.has('mobile')) techVibe = "a native mobile implementation (Swift/Kotlin)";

        // Get the primary user interaction from their path
        const primaryInteraction = userPath.length > 1 ? userPath[1].toLowerCase() : "its core features";

        // Build the prompt string
        let promptText = `**Vibe-Driven App Generation Request**\n\n`;
        promptText += `**1. High-Level Concept:**\n`;
        promptText += `Create ${goal}. The application should be centered around the idea of ${primaryInteraction}.\n\n`;

        promptText += `**2. Core Vibe & Key Tags:**\n`;
        promptText += `The overall vibe should be guided by the following concepts. These tags represent the core DNA of the application:\n`;
        promptText += `- ${Array.from(userTags).join('\n- ')}\n\n`;

        promptText += `**3. Tech Stack Vibe:**\n`;
        promptText += `The implementation should follow the principles of ${techVibe}. Focus on creating code that is clean, maintainable, and reflects this choice.\n\n`;

        promptText += `**Instructions for the Vibe Coder:**\n`;
        promptText += `Generate a functional prototype based on this specification. The user interface should be intuitive and the user experience seamless. The generated code should be well-structured and embody the 'vibe' described by the tags above.`;

        promptEl.value = promptText;
    }

    copyButton.addEventListener('click', () => {
        promptEl.select();
        document.execCommand('copy');
        alert('Prompt copied to clipboard!');
    });

    // Start the wizard
    start();
});
