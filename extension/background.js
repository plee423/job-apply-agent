// Background service worker
// Handles: opening side panel, receiving job data, calling Anthropic API

let latestJobData = null;

// Open side panel when extension icon is clicked
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ windowId: tab.windowId });
});

// Receive extracted job data from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'JOB_EXTRACTED') {
    latestJobData = message.payload;
    // Forward to side panel if it's open
    chrome.runtime.sendMessage({
      type: 'JOB_DATA_READY',
      payload: latestJobData,
    }).catch(() => {
      // Side panel not open yet, data is stored in latestJobData
    });
  }

  if (message.type === 'GET_LATEST_JOB') {
    sendResponse({ payload: latestJobData });
    return true;
  }

  if (message.type === 'GENERATE') {
    handleGenerate(message.payload, sender);
    return true;
  }
});

async function handleGenerate({ jobText, contentTypes, model }) {
  // Load profile and template files from storage
  const storage = await chrome.storage.local.get([
    'apiKey', 'resume', 'stories', 'preferences',
    'tpl_cold_email', 'tpl_linkedin', 'tpl_cover_letter',
    'tpl_referral', 'tpl_slack'
  ]);

  const apiKey = storage.apiKey;
  if (!apiKey) {
    chrome.runtime.sendMessage({ type: 'ERROR', message: 'No API key. Go to extension settings.' });
    return;
  }

  const systemPrompt = buildSystemPrompt(storage);
  const userMessage = buildUserMessage(jobText, contentTypes);

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: model || 'claude-sonnet-4-6',
        max_tokens: 4096,
        system: systemPrompt,
        messages: [{ role: 'user', content: userMessage }],
        stream: true,
      }),
    });

    if (!response.ok) {
      const err = await response.json();
      chrome.runtime.sendMessage({ type: 'ERROR', message: err.error?.message || 'API error' });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(l => l.startsWith('data: '));

      for (const line of lines) {
        const data = line.slice(6);
        if (data === '[DONE]') continue;

        try {
          const parsed = JSON.parse(data);
          if (parsed.type === 'content_block_delta' && parsed.delta?.type === 'text_delta') {
            chrome.runtime.sendMessage({
              type: 'STREAM_CHUNK',
              text: parsed.delta.text,
            }).catch(() => {});
          }
          if (parsed.type === 'message_stop') {
            chrome.runtime.sendMessage({ type: 'STREAM_DONE' }).catch(() => {});
          }
        } catch (_) {}
      }
    }
  } catch (err) {
    chrome.runtime.sendMessage({ type: 'ERROR', message: err.message }).catch(() => {});
  }
}

function buildSystemPrompt(storage) {
  const resume = storage.resume || '[Resume not set up yet. Go to extension settings to import your profile.]';
  const stories = storage.stories || '[Stories not set up yet.]';
  const preferences = storage.preferences || '[Preferences not set up yet.]';
  const tplColdEmail = storage.tpl_cold_email || '';
  const tplLinkedin = storage.tpl_linkedin || '';
  const tplCoverLetter = storage.tpl_cover_letter || '';
  const tplReferral = storage.tpl_referral || '';
  const tplSlack = storage.tpl_slack || '';

  return `You are a world-class career coach and copywriter. Generate hyper-personalized job application content.

=== CANDIDATE RESUME ===
${resume}

=== CANDIDATE PROFESSIONAL STORIES (STAR FORMAT) ===
${stories}

=== COMMUNICATION PREFERENCES & BRAND RULES ===
${preferences}

=== TEMPLATES TO FOLLOW ===

--- COLD EMAIL TEMPLATE ---
${tplColdEmail}

--- LINKEDIN MESSAGE TEMPLATE ---
${tplLinkedin}

--- COVER LETTER TEMPLATE ---
${tplCoverLetter}

--- REFERRAL REQUEST TEMPLATE ---
${tplReferral}

--- SLACK MESSAGE TEMPLATE ---
${tplSlack}

=== INSTRUCTIONS ===
When given a job posting:
1. Extract: company name, role title, key requirements, culture signals, pain points.
2. Match the candidate's most relevant experience and stories to the role requirements.
3. Generate ONLY the content types requested.
4. Follow each template's structure and constraints exactly.
5. Every piece must be specific to THIS company and role — never generic.
6. Include at least one concrete metric per piece.
7. Never use "I'm passionate about", "I came across your posting", or generic openers.
8. Format EXACTLY like this — use these exact separators:
   ═══ [CONTENT TYPE NAME] ═══
   [content]
   ═══ END ═══
9. After all content, add a "Why This Works" section with 2-3 strategic bullets.`;
}

function buildUserMessage(jobText, contentTypes) {
  const types = contentTypes && contentTypes.length > 0
    ? contentTypes.join(', ')
    : 'Cold Email (Hiring Manager), Cold Email (Recruiter), LinkedIn Connection Request, LinkedIn Follow-up Message, Cover Letter, Referral Request, Slack Message';

  return `Generate the following content types: ${types}

JOB POSTING:
${jobText}`;
}
