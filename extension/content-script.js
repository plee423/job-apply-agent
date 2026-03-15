// Content script: runs on job board pages, extracts job description
// Sends extracted data to the background service worker

(function () {
  const hostname = window.location.hostname;

  function extractLinkedIn() {
    const titleEl = document.querySelector(
      '.job-details-jobs-unified-top-card__job-title h1, ' +
      '.jobs-unified-top-card__job-title h1, ' +
      '.topcard__title, ' +
      'h1[class*="job-title"]'
    );
    const companyEl = document.querySelector(
      '.job-details-jobs-unified-top-card__company-name a, ' +
      '.jobs-unified-top-card__company-name a, ' +
      '.topcard__org-name-link, ' +
      'a[class*="company-name"]'
    );
    const descEl = document.querySelector(
      '.jobs-description-content__text, ' +
      '.jobs-description__content, ' +
      '.description__text, ' +
      '[class*="job-description"]'
    );

    return {
      title: titleEl?.innerText?.trim() || null,
      company: companyEl?.innerText?.trim() || null,
      description: descEl?.innerText?.trim() || null,
    };
  }

  function extractGreenhouse() {
    const titleEl = document.querySelector('h1.app-title, #header h1');
    const companyEl = document.querySelector('.company-name, [class*="company"]');
    const descEl = document.querySelector('#content, .section-wrapper, .job-post');

    return {
      title: titleEl?.innerText?.trim() || null,
      company: companyEl?.innerText?.trim() || null,
      description: descEl?.innerText?.trim() || null,
    };
  }

  function extractLever() {
    const titleEl = document.querySelector('.posting-headline h2, h2.posting-name');
    const companyEl = document.querySelector('.main-header-logo img');
    const descEl = document.querySelector('.posting-page .section-wrapper, .posting-content');

    return {
      title: titleEl?.innerText?.trim() || null,
      company: companyEl?.alt?.trim() || document.title.split(' - ')[1]?.trim() || null,
      description: descEl?.innerText?.trim() || null,
    };
  }

  function extractWorkday() {
    const titleEl = document.querySelector(
      '[data-automation-id="jobPostingHeader"] h2, ' +
      '[data-automation-id="jobPostingTitle"]'
    );
    const companyEl = document.querySelector('[data-automation-id="appName"]');
    const descEl = document.querySelector('[data-automation-id="jobPostingDescription"]');

    return {
      title: titleEl?.innerText?.trim() || null,
      company: companyEl?.innerText?.trim() || null,
      description: descEl?.innerText?.trim() || null,
    };
  }

  function extractAshby() {
    const titleEl = document.querySelector('h1[class*="title"], .job-title h1');
    const companyEl = document.querySelector('[class*="company"], .org-name');
    const descEl = document.querySelector('[class*="description"], [class*="content"] .prose');

    return {
      title: titleEl?.innerText?.trim() || null,
      company: companyEl?.innerText?.trim() || null,
      description: descEl?.innerText?.trim() || null,
    };
  }

  function extractGeneric() {
    // Heuristic: find the largest block of text that likely contains job content
    const candidates = Array.from(document.querySelectorAll(
      'main, article, [role="main"], .job-description, .description, #job-description, #description, .content'
    ));

    const jobKeywords = ['responsibilities', 'requirements', 'qualifications', 'experience', 'skills', 'benefits', 'about the role', 'what you\'ll do'];

    let best = null;
    let bestScore = 0;

    for (const el of candidates) {
      const text = el.innerText || '';
      const wordCount = text.split(/\s+/).length;
      const keywordMatches = jobKeywords.filter(kw => text.toLowerCase().includes(kw)).length;
      const score = wordCount * 0.5 + keywordMatches * 100;

      if (score > bestScore) {
        bestScore = score;
        best = el;
      }
    }

    // Fallback: just grab the body text if nothing matched
    if (!best || bestScore < 50) {
      best = document.body;
    }

    const titleEl = document.querySelector('h1');
    const metaCompany = document.querySelector('meta[property="og:site_name"], meta[name="author"]');

    return {
      title: titleEl?.innerText?.trim() || document.title,
      company: metaCompany?.content?.trim() || null,
      description: best?.innerText?.trim() || null,
    };
  }

  // Pick the right extractor
  let result = null;

  if (hostname.includes('linkedin.com')) {
    result = extractLinkedIn();
  } else if (hostname.includes('greenhouse.io')) {
    result = extractGreenhouse();
  } else if (hostname.includes('lever.co')) {
    result = extractLever();
  } else if (hostname.includes('workday.com') || hostname.includes('myworkdayjobs.com')) {
    result = extractWorkday();
  } else if (hostname.includes('ashbyhq.com')) {
    result = extractAshby();
  } else {
    result = extractGeneric();
  }

  // If site-specific extractor got a description, use it. Otherwise fall back to generic.
  if (!result?.description) {
    const generic = extractGeneric();
    result = {
      title: result?.title || generic.title,
      company: result?.company || generic.company,
      description: generic.description,
    };
  }

  // Clean up excessive whitespace
  if (result.description) {
    result.description = result.description
      .replace(/\n{3,}/g, '\n\n')
      .replace(/\t/g, ' ')
      .trim()
      .slice(0, 8000); // cap at 8000 chars to avoid token bloat
  }

  result.url = window.location.href;

  // Send to background service worker (which forwards to side panel)
  chrome.runtime.sendMessage({
    type: 'JOB_EXTRACTED',
    payload: result,
  });
})();
