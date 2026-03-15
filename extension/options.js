// Options page logic

const PROFILE_KEYS = ['resume', 'stories', 'preferences'];
const PLACEHOLDER_MARKER = '[Your Full Name]'; // detect unfilled template

async function loadSettings() {
  const storage = await chrome.storage.local.get(['apiKey', 'model', ...PROFILE_KEYS]);

  if (storage.apiKey) {
    document.getElementById('api-key').value = storage.apiKey;
  }
  if (storage.model) {
    document.getElementById('model').value = storage.model;
  }

  updateProfileDots(storage);
}

function updateProfileDots(storage) {
  PROFILE_KEYS.forEach(key => {
    const dot = document.getElementById(`dot-${key === 'preferences' ? 'prefs' : key}`);
    const content = storage[key] || '';
    if (!content) {
      dot.className = 'status-dot'; // grey = not uploaded
    } else if (content.includes(PLACEHOLDER_MARKER) || content.includes('[Your Full Name]') || content.includes('[fill')) {
      dot.className = 'status-dot warn'; // yellow = has placeholders
    } else {
      dot.className = 'status-dot ok'; // green = looks filled in
    }
  });
}

async function saveSettings() {
  const apiKey = document.getElementById('api-key').value.trim();
  const model = document.getElementById('model').value;

  const dataToSave = { apiKey, model };

  // Read any newly selected files
  const fileInputs = {
    resume: document.getElementById('file-resume'),
    stories: document.getElementById('file-stories'),
    preferences: document.getElementById('file-preferences'),
  };

  const fileReadPromises = Object.entries(fileInputs).map(([key, input]) => {
    if (input.files && input.files[0]) {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve([key, e.target.result]);
        reader.readAsText(input.files[0]);
      });
    }
    return Promise.resolve(null);
  });

  const fileResults = await Promise.all(fileReadPromises);
  fileResults.forEach(result => {
    if (result) {
      const [key, content] = result;
      dataToSave[key] = content;
    }
  });

  await chrome.storage.local.set(dataToSave);

  // Show saved confirmation
  const status = document.getElementById('save-status');
  status.classList.add('visible');
  setTimeout(() => status.classList.remove('visible'), 2500);

  // Refresh dots
  const storage = await chrome.storage.local.get(PROFILE_KEYS);
  updateProfileDots({ ...storage, ...dataToSave });
}

async function clearFile(key) {
  await chrome.storage.local.remove([key]);
  const input = document.getElementById(`file-${key === 'preferences' ? 'preferences' : key}`);
  if (input) input.value = '';
  const storage = await chrome.storage.local.get(PROFILE_KEYS);
  updateProfileDots(storage);
}

document.getElementById('btn-save').addEventListener('click', saveSettings);

loadSettings();
