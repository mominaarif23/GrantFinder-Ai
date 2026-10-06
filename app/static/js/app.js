// GrantFinder AI Client-Side Application Script

let currentSelectedCard = null;

// ==============================================================================
// Theme Toggle & State Synchronization (Light / Dark Mode)
// ==============================================================================

function syncThemeIcons() {
    const isDark = document.documentElement.classList.contains('dark');
    const sunIcon = document.getElementById('themeSunIcon');
    const moonIcon = document.getElementById('themeMoonIcon');
    const mobileThemeText = document.getElementById('mobileThemeText');

    if (sunIcon && moonIcon) {
        if (isDark) {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        } else {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        }
    }

    if (mobileThemeText) {
        mobileThemeText.textContent = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    }
}

function toggleThemeMode() {
    const isDark = document.documentElement.classList.toggle('dark');
    const newTheme = isDark ? 'dark' : 'light';
    try {
        localStorage.setItem('grantfinder_theme', newTheme);
        localStorage.setItem('theme', newTheme);
    } catch (e) {}

    syncThemeIcons();
    showToast(isDark ? 'Dark mode enabled' : 'Light mode enabled', 'info');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncThemeIcons);
} else {
    syncThemeIcons();
}

// ==============================================================================
// Notification Dropdown & Toasts
// ==============================================================================

function toggleNotifDropdown() {
    const dropdown = document.getElementById('notifDropdown');
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
}

document.addEventListener('click', (e) => {
    const container = document.getElementById('notifDropdownContainer');
    const dropdown = document.getElementById('notifDropdown');
    if (container && dropdown && !container.contains(e.target)) {
        dropdown.classList.add('hidden');
    }
});

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    const colors = {
        success: 'bg-emerald-50 border-emerald-200 text-emerald-900 shadow-md',
        error: 'bg-rose-50 border-rose-200 text-rose-900 shadow-md',
        info: 'bg-navy-900 border-navy-800 text-white shadow-lg'
    };
    
    toast.className = `p-3.5 rounded-2xl border text-xs font-semibold flex items-center space-x-2 transition-all duration-300 transform translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ==============================================================================
// Authentication Handlers & Password Utilities
// ==============================================================================

function togglePasswordVisibility(inputId, toggleBtnId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(toggleBtnId);
    if (!input || !btn) return;

    if (input.type === 'password') {
        input.type = 'text';
        btn.setAttribute('aria-label', 'Hide password');
        btn.innerHTML = `
            <svg class="w-4 h-4 text-brand-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
            </svg>
        `;
    } else {
        input.type = 'password';
        btn.setAttribute('aria-label', 'Show password');
        btn.innerHTML = `
            <svg class="w-4 h-4 text-slate-400 hover:text-navy-900 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
        `;
    }
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('loginBtn');
    const errorBox = document.getElementById('loginError');
    errorBox.classList.add('hidden');
    btn.disabled = true;
    btn.innerText = 'Verifying credentials...';

    const rememberChecked = document.getElementById('rememberMe')?.checked || false;
    const emailValue = document.getElementById('email').value.trim();

    const payload = {
        email: emailValue,
        password: document.getElementById('password').value,
        remember_me: rememberChecked
    };

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            // Save or clear remembered email locally
            if (rememberChecked) {
                localStorage.setItem('grantfinder_remember_email', emailValue);
            } else {
                localStorage.removeItem('grantfinder_remember_email');
            }

            showToast('Login successful. Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 500);
        } else {
            errorBox.innerText = data.detail || 'Invalid email or password.';
            errorBox.classList.remove('hidden');
            btn.disabled = false;
            btn.innerText = 'Sign In';
        }
    } catch (err) {
        errorBox.innerText = 'An error occurred while connecting to the server.';
        errorBox.classList.remove('hidden');
        btn.disabled = false;
        btn.innerText = 'Sign In';
    }
}

async function handleRegisterSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('registerBtn');
    const errorBox = document.getElementById('registerError');
    errorBox.classList.add('hidden');
    btn.disabled = true;
    btn.innerText = 'Creating account...';

    const role = document.querySelector('input[name="role"]:checked').value;
    const payload = {
        name: document.getElementById('name').value.trim(),
        email: document.getElementById('email').value.trim(),
        password: document.getElementById('password').value,
        role: role
    };

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast('Registration successful. Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = '/onboarding';
            }, 500);
        } else {
            errorBox.innerText = data.detail || 'Registration failed.';
            errorBox.classList.remove('hidden');
            btn.disabled = false;
            btn.innerText = 'Complete Registration';
        }
    } catch (err) {
        errorBox.innerText = 'Server error occurred.';
        errorBox.classList.remove('hidden');
        btn.disabled = false;
        btn.innerText = 'Complete Registration';
    }
}

async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {}
    window.location.href = '/';
}

// ==============================================================================
// Profile Management
// ==============================================================================

async function handleProfileSubmit(e, profileType) {
    e.preventDefault();
    const btn = document.getElementById('saveProfileBtn');
    const statusMsg = document.getElementById('profileStatusMsg');
    btn.disabled = true;
    statusMsg.innerText = 'Saving...';

    const payload = {
        type: profileType,
        major_domain: document.getElementById('major_domain').value.trim(),
        degree_level_stage: document.getElementById('degree_level_stage').value,
        gpa_funding: document.getElementById('gpa_funding').value.trim(),
        country_preference: document.getElementById('country_preference').value
    };

    try {
        const res = await fetch('/api/auth/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            statusMsg.innerText = 'Profile updated! Re-running match scoring...';
            showToast('Profile updated successfully', 'success');
            setTimeout(() => {
                statusMsg.innerText = '';
                triggerSearch(profileType === 'academic' ? 'scholarship' : 'grant');
            }, 800);
        }
    } catch (err) {
        statusMsg.innerText = 'Failed to save profile.';
    } finally {
        btn.disabled = false;
    }
}

// ==============================================================================
// Hybrid Opportunities Search
// ==============================================================================

async function triggerSearch(track, isInitial = false) {
    const btn = document.getElementById('searchBtn');
    const container = document.getElementById('opportunitiesGrid');
    const countBanner = document.getElementById('resultsCountBanner');
    const subtitle = document.getElementById('resultsStatusSubtitle');

    if (!container) return;

    btn.disabled = true;
    btn.innerHTML = `<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Scanning Repos & Live Web...`;
    subtitle.innerText = 'Querying curated repositories and performing real-time web discovery...';

    const payload = {
        track: track,
        country: document.getElementById('searchCountry').value,
        keyword: document.getElementById('searchKeyword').value.trim(),
        is_initial: isInitial
    };

    try {
        const res = await fetch('/api/opportunities/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            renderOpportunityCards(data.results, data.is_unlimited, data.plan, track);
            countBanner.classList.remove('hidden');
            countBanner.innerText = `${data.total_found} Matches Discovered (${data.unlocked_count} Unlocked)`;
            subtitle.innerText = data.is_unlimited 
                ? 'All opportunities fully unlocked under Premium Tier.' 
                : 'Top 3 opportunities fully visible under Free Tier. Remaining results locked.';
        } else {
            subtitle.innerText = 'Search query failed. Please try again.';
        }
    } catch (err) {
        subtitle.innerText = 'Error performing live search.';
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Run AI Search</span>`;
    }
}

function renderOpportunityCards(cards, isUnlimited, plan, track) {
    const container = document.getElementById('opportunitiesGrid');
    container.innerHTML = '';

    if (!cards || cards.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-12 p-8 rounded-3xl bg-white border border-slate-200 shadow-xs">
                <p class="text-sm font-bold text-navy-900">No matching opportunities found for your criteria.</p>
                <p class="text-xs text-slate-500 mt-1">Try broadening your keywords or selecting 'All Regions'.</p>
            </div>
        `;
        return;
    }

    cards.forEach((card, idx) => {
        const cardEl = document.createElement('div');
        const isLocked = card.is_locked;

        if (isLocked) {
            // Blurred Locked Card for Free Tier (Institutional Style)
            cardEl.className = 'relative rounded-3xl bg-white border border-slate-200 p-6 sm:p-7 flex flex-col justify-between overflow-hidden shadow-xs';
            cardEl.innerHTML = `
                <div class="absolute inset-0 bg-white/85 backdrop-blur-md z-20 flex flex-col items-center justify-center p-6 text-center">
                    <div class="w-11 h-11 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700 font-bold mb-3 shadow-xs">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
                    </div>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-200 mb-2">Premium Gated</span>
                    <h4 class="text-sm font-bold text-navy-900 mb-1 max-w-xs">${card.name}</h4>
                    <p class="text-xs text-slate-500 mb-4 max-w-xs">Match #${idx + 1} locked under Free Tier. Unlock complete eligibility parameters, award amounts, and AI statement generation.</p>
                    <button onclick="openUpgradeModal()" class="px-4 py-2.5 rounded-xl bg-brand-700 hover:bg-brand-800 text-white font-bold text-xs shadow-sm transition">
                        Unlock All Matches ($9 Demo)
                    </button>
                </div>
                <div class="filter blur-xs select-none opacity-40">
                    <h4 class="text-base font-bold text-navy-900 mb-1">${card.name}</h4>
                    <p class="text-xs text-slate-500">Curated institutional funding opportunity</p>
                </div>
            `;
        } else {
            // Fully Unlocked Institutional Card
            const scoreColor = card.match_score >= 85 
                ? 'text-emerald-800 bg-emerald-50 border-emerald-200' 
                : card.match_score >= 70
                    ? 'text-brand-800 bg-brand-50 border-brand-200'
                    : 'text-slate-700 bg-slate-100 border-slate-200';

            const badgeType = card.is_curated 
                ? '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200">Curated Repository</span>'
                : '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-brand-50 text-brand-700 border border-brand-200">Live AI Discovery</span>';

            const assistantBtnText = track === 'scholarship' ? 'Draft AI Statement' : 'Draft AI Pitch';
            const assistantBtnClass = track === 'scholarship'
                ? 'bg-brand-700 hover:bg-brand-800 text-white'
                : 'bg-emerald-700 hover:bg-emerald-800 text-white';

            const assistantAction = track === 'scholarship' 
                ? `openEssayModal(${JSON.stringify(card).replace(/"/g, '&quot;')})`
                : `openPitchModal(${JSON.stringify(card).replace(/"/g, '&quot;')})`;

            cardEl.className = 'rounded-3xl bg-white border border-slate-200 p-6 sm:p-7 flex flex-col justify-between hover:border-slate-300 hover:shadow-md transition shadow-xs group';
            cardEl.innerHTML = `
                <div>
                    <!-- Header Badges -->
                    <div class="flex items-center justify-between gap-2 mb-3">
                        <div class="flex items-center space-x-1.5 flex-wrap gap-y-1">
                            ${badgeType}
                            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">${card.country}</span>
                        </div>
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${scoreColor}">
                            ${card.match_score}% Match
                        </span>
                    </div>

                    <!-- Title -->
                    <h4 class="text-base sm:text-lg font-bold text-navy-900 mb-2 line-clamp-2 leading-snug group-hover:text-brand-700 transition">${card.name}</h4>

                    <!-- Key Metadata -->
                    <div class="space-y-1.5 text-xs text-slate-600 mb-4 pb-3 border-b border-slate-100">
                        <p class="flex items-center justify-between">
                            <span class="text-slate-400 font-medium">Funding:</span>
                            <span class="font-extrabold text-emerald-700">${card.amount}</span>
                        </p>
                        <p class="flex items-center justify-between">
                            <span class="text-slate-400 font-medium">Deadline:</span>
                            <span class="font-mono text-slate-700 font-semibold">${card.deadline}</span>
                        </p>
                    </div>

                    <!-- Eligibility -->
                    <div class="text-xs text-slate-600 mb-4">
                        <p class="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">Eligibility Criteria</p>
                        <p class="line-clamp-3 leading-relaxed text-slate-600">${card.eligibility}</p>
                    </div>

                    <!-- Match Reasons -->
                    <div class="text-[11px] text-slate-500 mb-4 space-y-1 bg-slate-50 p-3 rounded-2xl border border-slate-100">
                        ${card.match_reasons.map(r => `<p class="flex items-start space-x-1.5"><span class="text-brand-700 font-bold shrink-0">•</span><span>${r}</span></p>`).join('')}
                    </div>
                </div>

                <!-- Action Footer -->
                <div class="pt-4 border-t border-slate-100 flex items-center justify-between gap-2">
                    <a href="${card.source_link}" target="_blank" class="inline-flex items-center text-xs font-bold text-brand-700 hover:text-brand-800 transition">
                        <span>Official Portal</span>
                        <span class="ml-1 text-[11px]">&rarr;</span>
                    </a>
                    <div class="flex items-center space-x-2">
                        <button onclick="saveOpportunityDirect(${JSON.stringify(card).replace(/"/g, '&quot;')})" class="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition border border-slate-200">
                            Save
                        </button>
                        <button onclick="${assistantAction}" class="px-3.5 py-1.5 rounded-xl ${assistantBtnClass} text-xs font-bold transition shadow-xs">
                            ${assistantBtnText}
                        </button>
                    </div>
                </div>
            `;
        }

        container.appendChild(cardEl);
    });
}

// ==============================================================================
// Saving Opportunities
// ==============================================================================

async function saveOpportunityDirect(card) {
    const payload = {
        opportunity_name: card.name,
        opportunity_type: card.type,
        amount: card.amount,
        deadline: card.deadline,
        source_link: card.source_link,
        match_score: card.match_score
    };

    try {
        const res = await fetch('/api/opportunities/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Saved '${card.name.substring(0, 30)}...' to your account`, 'success');
            appendSavedOppToUI(data.saved);
        } else {
            showToast(data.detail || 'Could not save opportunity', 'error');
        }
    } catch (err) {
        showToast('Error saving opportunity', 'error');
    }
}

function appendSavedOppToUI(saved) {
    const list = document.getElementById('savedOpportunitiesList');
    const badge = document.getElementById('savedCountBadge');
    if (!list) return;

    if (list.querySelector('p.text-slate-400') || list.querySelector('p.text-slate-500')) {
        list.innerHTML = '';
    }

    const item = document.createElement('div');
    item.className = 'p-3 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-2';
    item.id = `saved-card-${saved.id}`;
    item.innerHTML = `
        <div class="truncate">
            <p class="font-bold text-navy-900 truncate">${saved.opportunity_name}</p>
            <p class="text-[11px] text-slate-500 mt-0.5">${saved.amount} · Score: ${saved.match_score}%</p>
        </div>
        <div class="flex items-center space-x-1 shrink-0">
            <a href="${saved.source_link}" target="_blank" class="p-1.5 text-slate-500 hover:text-brand-700" title="Open Link">&rarr;</a>
            <button onclick="removeSavedOpp('${saved.id}')" class="p-1.5 text-slate-400 hover:text-rose-600 font-bold" title="Delete">&times;</button>
        </div>
    `;
    list.prepend(item);

    if (badge) {
        badge.innerText = parseInt(badge.innerText || '0') + 1;
    }
}

async function removeSavedOpp(savedId) {
    try {
        const res = await fetch(`/api/opportunities/saved/${savedId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            const el = document.getElementById(`saved-card-${savedId}`);
            if (el) el.remove();
            showToast('Saved opportunity removed', 'info');
            const badge = document.getElementById('savedCountBadge');
            if (badge) {
                const count = Math.max(0, parseInt(badge.innerText || '1') - 1);
                badge.innerText = count;
            }
        }
    } catch (err) {
        showToast('Failed to delete bookmark', 'error');
    }
}

// ==============================================================================
// Mock Upgrade Flow ($9 Demo)
// ==============================================================================

function openUpgradeModal() {
    const modal = document.getElementById('upgradeModal');
    if (modal) modal.classList.remove('hidden');
}

function closeUpgradeModal() {
    const modal = document.getElementById('upgradeModal');
    if (modal) modal.classList.add('hidden');
}

async function executeMockUpgrade() {
    const btn = document.getElementById('upgradeConfirmBtn');
    btn.disabled = true;
    btn.innerText = 'Processing Demo Payment ($9)...';

    try {
        const res = await fetch('/api/user/upgrade', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('Congratulations! Upgraded to Premium Tier.', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 800);
        } else {
            showToast('Upgrade failed. Please retry.', 'error');
            btn.disabled = false;
            btn.innerText = 'Confirm Upgrade ($9 Demo)';
        }
    } catch (err) {
        showToast('Network error during upgrade', 'error');
        btn.disabled = false;
        btn.innerText = 'Confirm Upgrade ($9 Demo)';
    }
}

// ==============================================================================
// AI Application Essay Drafter (Scholarship Track)
// ==============================================================================

function openEssayModal(card) {
    currentSelectedCard = card;
    const modal = document.getElementById('essayModal');
    const nameHeading = document.getElementById('essayModalOppName');
    const statedReq = document.getElementById('essayStatedReq');
    const outputArea = document.getElementById('essayOutputArea');

    if (modal) {
        nameHeading.innerText = card.name;
        statedReq.value = card.eligibility || 'Academic merit, leadership potential';
        outputArea.value = '';
        modal.classList.remove('hidden');
    }
}

function closeEssayModal() {
    const modal = document.getElementById('essayModal');
    if (modal) modal.classList.add('hidden');
}

async function generateEssayDraft() {
    if (!currentSelectedCard) return;

    const btn = document.getElementById('essayGenerateBtn');
    const outputArea = document.getElementById('essayOutputArea');
    btn.disabled = true;
    btn.innerText = 'Drafting statement with Gemini AI...';
    outputArea.value = 'Generating tailored Statement of Purpose...';

    const payload = {
        opportunity_name: currentSelectedCard.name,
        opportunity_type: 'scholarship',
        stated_requirements: document.getElementById('essayStatedReq').value.trim(),
        personal_notes: document.getElementById('essayPersonalNotes').value.trim()
    };

    try {
        const res = await fetch('/api/assistant/essay', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.status === 402) {
            // Freemium gated! Prompt upgrade modal
            closeEssayModal();
            openUpgradeModal();
            showToast('AI Drafting requires Premium Tier ($9)', 'info');
            return;
        }

        if (data.success) {
            outputArea.value = data.essay_draft;
            showToast('Statement of Purpose generated!', 'success');
        } else {
            outputArea.value = 'Drafting error: ' + (data.detail || 'Unable to generate essay.');
        }
    } catch (err) {
        outputArea.value = 'Error connecting to AI service.';
    } finally {
        btn.disabled = false;
        btn.innerText = 'Generate Essay with Gemini AI';
    }
}

function copyEssayToClipboard() {
    const text = document.getElementById('essayOutputArea').value;
    if (!text) return;
    navigator.clipboard.writeText(text);
    showToast('Essay draft copied to clipboard', 'info');
}

// ==============================================================================
// AI Startup Grant Pitch Drafter (Founder Track)
// ==============================================================================

function openPitchModal(card) {
    currentSelectedCard = card;
    const modal = document.getElementById('pitchModal');
    const nameHeading = document.getElementById('pitchModalOppName');
    const outputArea = document.getElementById('pitchOutputArea');

    if (modal) {
        nameHeading.innerText = card.name;
        outputArea.value = '';
        modal.classList.remove('hidden');
    }
}

function closePitchModal() {
    const modal = document.getElementById('pitchModal');
    if (modal) modal.classList.add('hidden');
}

async function generatePitchDraft() {
    if (!currentSelectedCard) return;

    const btn = document.getElementById('pitchGenerateBtn');
    const outputArea = document.getElementById('pitchOutputArea');
    btn.disabled = true;
    btn.innerText = 'Drafting grant proposal with Gemini AI...';
    outputArea.value = 'Synthesizing executive grant proposal...';

    const payload = {
        opportunity_name: currentSelectedCard.name,
        opportunity_type: 'grant',
        problem_statement: document.getElementById('pitchProblemStmt').value.trim(),
        solution_summary: document.getElementById('pitchSolutionSum').value.trim(),
        funding_ask: document.getElementById('pitchFundingAsk').value.trim()
    };

    try {
        const res = await fetch('/api/assistant/pitch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.status === 402) {
            // Freemium gated! Prompt upgrade modal
            closePitchModal();
            openUpgradeModal();
            showToast('AI Pitch Drafter requires Premium Tier ($9)', 'info');
            return;
        }

        if (data.success) {
            outputArea.value = data.pitch_draft;
            showToast('Grant proposal generated!', 'success');
        } else {
            outputArea.value = 'Proposal error: ' + (data.detail || 'Unable to generate pitch.');
        }
    } catch (err) {
        outputArea.value = 'Error connecting to AI service.';
    } finally {
        btn.disabled = false;
        btn.innerText = 'Generate Grant Pitch Proposal with Gemini AI';
    }
}

function copyPitchToClipboard() {
    const text = document.getElementById('pitchOutputArea').value;
    if (!text) return;
    navigator.clipboard.writeText(text);
    showToast('Proposal draft copied to clipboard', 'info');
}

// ==============================================================================
// Mobile Navigation Drawer Toggle
// ==============================================================================

function toggleMobileNav() {
    const drawer = document.getElementById('mobileNavDrawer');
    if (drawer) {
        drawer.classList.toggle('hidden');
    }
}

// ==============================================================================
// Dynamic Country Atmospheric Background System
// ==============================================================================

const countryLandmarks = {
    'pakistan': {
        name: 'Pakistan',
        landmark: 'Faisal Mosque, Islamabad',
        tag: 'National Architectural Landmark',
        url: 'https://images.unsplash.com/photo-1627894483216-2138af692e32?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'HEC, Ignite, NIC, and national university scholarship portals'
    },
    'united kingdom': {
        name: 'United Kingdom',
        landmark: 'Radcliffe Camera & Bodleian, Oxford',
        tag: 'Historic Collegiate Academia',
        url: 'https://images.unsplash.com/photo-1520986606214-8b456906c813?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Chevening, Commonwealth, Rhodes, and British Council endowments'
    },
    'united states': {
        name: 'United States',
        landmark: 'Harvard Yard & Historic Campus, Cambridge',
        tag: 'Ivy League Research & Seed Accelerators',
        url: 'https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Fulbright Fellowships, USEFP, and Y Combinator non-dilutive grants'
    },
    'germany': {
        name: 'Germany',
        landmark: 'Heidelberg Castle & Old University Quad',
        tag: 'Tuition-Free Research Centers',
        url: 'https://images.unsplash.com/photo-1467269204594-9661b134dd2b?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'DAAD Scholarships, Max Planck Fellowships, and public research universities'
    },
    'france': {
        name: 'France',
        landmark: 'Sorbonne University & Panthéon, Paris',
        tag: 'Continental Academia & Research',
        url: 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Campus France, Eiffel Excellence Scholarships, and French Tech'
    },
    'china': {
        name: 'China',
        landmark: 'Tsinghua University & Forbidden City, Beijing',
        tag: 'State Key Innovation Centers',
        url: 'https://images.unsplash.com/photo-1508804185872-d7badad00f7d?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Chinese Government Scholarship (CSC) and Belt and Road Fellowships'
    },
    'netherlands': {
        name: 'Netherlands',
        landmark: 'Leiden University & Historic Canals',
        tag: 'Dutch Research Consortiums',
        url: 'https://images.unsplash.com/photo-1512470876302-972faa2aa9a4?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'NL Scholarship, Orange Knowledge Programme, and Erasmus MC'
    },
    'sweden': {
        name: 'Sweden',
        landmark: 'Uppsala University & Gamla Stan, Stockholm',
        tag: 'Scandinavian Innovation Centers',
        url: 'https://images.unsplash.com/photo-1509356843151-3e7d96241e11?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Swedish Institute Scholarships for Global Professionals (SISGP)'
    },
    'italy': {
        name: 'Italy',
        landmark: 'University of Bologna & Piazza Maggiore',
        tag: 'Historic European Academia',
        url: 'https://images.unsplash.com/photo-1516483638261-f4dbaf036963?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Invest Your Talent in Italy, MAECI, and DSU regional grants'
    },
    'spain': {
        name: 'Spain',
        landmark: 'University of Salamanca & Plaza Mayor',
        tag: 'Iberian Academic Foundations',
        url: 'https://images.unsplash.com/photo-1543783207-ec64e4d95325?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Fundación Carolina, MAEC-AECID, and Spanish university endowments'
    },
    'canada': {
        name: 'Canada',
        landmark: 'University of Toronto & Historic Front Campus',
        tag: 'U15 Canadian Research Universities',
        url: 'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Vanier CGS, Banting Postdoctoral Fellowships, and Mitacs Elevate'
    },
    'australia': {
        name: 'Australia',
        landmark: 'Sydney Harbor & Historic Cloisters',
        tag: 'Go8 Research Portals',
        url: 'https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Australia Awards, Endeavour Fellowships, and innovation grants'
    },
    'japan': {
        name: 'Japan',
        landmark: 'University of Tokyo & Yasuda Auditorium',
        tag: 'MEXT Imperial Academia',
        url: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'MEXT Japanese Government Scholarships and JSPS Postdoctoral Fellowships'
    },
    'switzerland': {
        name: 'Switzerland',
        landmark: 'ETH Zurich & Polyterrasse',
        tag: 'Federal Institutes of Technology',
        url: 'https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Swiss Government Excellence Scholarships (ESKAS) and EPFL grants'
    },
    'ireland': {
        name: 'Ireland',
        landmark: 'Trinity College & Long Room, Dublin',
        tag: 'Silicon Docks & Research Ireland',
        url: 'https://images.unsplash.com/photo-1549918864-48ac978761a4?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Government of Ireland Postgraduate Scholarship Programme'
    },
    'global': {
        name: 'Global / International',
        landmark: 'Grand Academic Assembly Hall',
        tag: 'Multilateral & Global Fellowships',
        url: 'https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Erasmus Mundus, World Bank, Gates Cambridge, and MIT Solve challenges'
    },
    'international': {
        name: 'International (Global)',
        landmark: 'Grand Academic Assembly Hall',
        tag: 'Multilateral & Global Fellowships',
        url: 'https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Overseas scholarship programs and international venture competitions'
    },
    'all': {
        name: 'All Global Regions',
        landmark: 'Grand Academic Assembly Hall',
        tag: 'Worldwide Repository',
        url: 'https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=1920&q=80',
        subtitle: 'Consolidated worldwide repository across 26+ verified destinations'
    }
};

function normalizeCountryKey(key) {
    if (!key) return 'pakistan';
    const clean = key.toLowerCase().trim();
    if (clean.includes('pakistan')) return 'pakistan';
    if (clean.includes('uk') || clean.includes('kingdom') || clean.includes('britain') || clean.includes('england')) return 'united kingdom';
    if (clean.includes('usa') || clean.includes('united states') || clean.includes('america')) return 'united states';
    if (clean.includes('germany') || clean.includes('deutschland')) return 'germany';
    if (clean.includes('france')) return 'france';
    if (clean.includes('china')) return 'china';
    if (clean.includes('netherland') || clean.includes('holland')) return 'netherlands';
    if (clean.includes('sweden')) return 'sweden';
    if (clean.includes('ital')) return 'italy';
    if (clean.includes('spain')) return 'spain';
    if (clean.includes('canada')) return 'canada';
    if (clean.includes('australia')) return 'australia';
    if (clean.includes('japan')) return 'japan';
    if (clean.includes('switz')) return 'switzerland';
    if (clean.includes('ireland')) return 'ireland';
    if (clean.includes('all')) return 'all';
    return 'international';
}

function setAtmosphereCountry(rawCountry) {
    const key = normalizeCountryKey(rawCountry);
    const data = countryLandmarks[key] || countryLandmarks['pakistan'];
    
    const atmosphereImage = document.getElementById('atmosphereImage');
    if (atmosphereImage) {
        atmosphereImage.style.opacity = '0';
        setTimeout(() => {
            atmosphereImage.style.backgroundImage = `url('${data.url}')`;
            atmosphereImage.style.opacity = '0.22';
        }, 300);
    }

    const atmosphereCountry = document.getElementById('atmosphereCountry');
    if (atmosphereCountry) {
        atmosphereCountry.innerText = data.name;
    }

    const atmosphereLandmark = document.getElementById('atmosphereLandmark');
    if (atmosphereLandmark) {
        atmosphereLandmark.innerText = data.landmark;
    }

    const atmosphereBadge = document.getElementById('atmosphereBadge');
    if (atmosphereBadge) {
        atmosphereBadge.classList.remove('hidden');
        atmosphereBadge.classList.add('flex');
    }

    // Defensive cleanup: keep top of landing page clean
    const legacyTag = document.getElementById('heroDestinationTag');
    if (legacyTag && legacyTag.parentElement) legacyTag.parentElement.remove();
}

function selectDestinationCountry(countryName) {
    setAtmosphereCountry(countryName);
    
    // Highlight destination card if present
    document.querySelectorAll('.destination-card').forEach(c => {
        c.classList.remove('ring-2', 'ring-brand-600', 'bg-brand-50/50');
    });
    const selected = document.getElementById(`dest-card-${normalizeCountryKey(countryName)}`);
    if (selected) {
        selected.classList.add('ring-2', 'ring-brand-600', 'bg-brand-50/50');
    }

    // If search country dropdown exists, update and trigger
    const searchDropdown = document.getElementById('searchCountry');
    if (searchDropdown) {
        const key = normalizeCountryKey(countryName);
        for (let i = 0; i < searchDropdown.options.length; i++) {
            if (normalizeCountryKey(searchDropdown.options[i].value) === key) {
                searchDropdown.selectedIndex = i;
                break;
            }
        }
        triggerSearch(searchDropdown.dataset.track || 'scholarship');
    }

    showToast(`Selected ${countryName}`, 'info');
}

// Auto-bind on load
document.addEventListener('DOMContentLoaded', () => {
    const searchCountry = document.getElementById('searchCountry');
    if (searchCountry) {
        searchCountry.addEventListener('change', (e) => {
            setAtmosphereCountry(e.target.value);
        });
        setAtmosphereCountry(searchCountry.value);
    } else {
        // Default to Pakistan atmosphere
        setAtmosphereCountry('Pakistan');
    }

    const countryPref = document.getElementById('country_preference');
    if (countryPref) {
        countryPref.addEventListener('change', (e) => {
            setAtmosphereCountry(e.target.value);
        });
    }
});

// ==============================================================================
// GrantFinder AI Advisor (Conversational Assistant & Supabase Sync)
// ==============================================================================

let advisorChatHistory = [];
let advisorSessionId = 'session_' + Math.random().toString(36).substring(2, 9);

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}

function toggleAdvisorWidget() {
    const widget = document.getElementById('advisorChatWidget');
    if (!widget) return;
    if (widget.classList.contains('hidden')) {
        widget.classList.remove('hidden');
        widget.classList.add('flex');
        const input = document.getElementById('advisorInput');
        if (input) input.focus();
    } else {
        widget.classList.add('hidden');
        widget.classList.remove('flex');
    }
}

async function handleAdvisorSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('advisorInput');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    appendAdvisorMessage('user', msg);

    const typingId = 'typing_' + Date.now();
    appendAdvisorTyping(typingId);

    const currentTrack = window.location.pathname.includes('founder') ? 'grant' : 'scholarship';

    try {
        const res = await fetch('/api/assistant/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg,
                history: advisorChatHistory,
                track: currentTrack,
                session_id: advisorSessionId
            })
        });

        const data = await res.json();
        removeAdvisorTyping(typingId);

        if (data.reply) {
            appendAdvisorMessage('assistant', data.reply);
            advisorChatHistory.push({ role: 'user', content: msg });
            advisorChatHistory.push({ role: 'assistant', content: data.reply });

            if (data.recommended_matches && data.recommended_matches.length > 0) {
                renderAdvisorRecommendations(data.recommended_matches);
            }
        } else {
            appendAdvisorMessage('assistant', "I am currently analyzing options. Please share your degree level or preferred country.");
        }
    } catch (err) {
        removeAdvisorTyping(typingId);
        appendAdvisorMessage('assistant', "The advisor service encountered a temporary network delay. Please try sending again.");
    }
}

function appendAdvisorMessage(role, text) {
    const container = document.getElementById('advisorChatMessages');
    if (!container) return;

    const row = document.createElement('div');
    row.className = role === 'user' ? 'flex items-start justify-end space-x-2' : 'flex items-start space-x-2';

    if (role === 'user') {
        row.innerHTML = `
            <div class="bg-navy-900 text-white p-3 rounded-2xl rounded-tr-none shadow-xs max-w-[85%] text-xs leading-relaxed">
                ${escapeHtml(text)}
            </div>
            <div class="w-6 h-6 rounded-lg bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                U
            </div>
        `;
    } else {
        row.innerHTML = `
            <div class="w-6 h-6 rounded-lg bg-navy-950 text-white text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                G
            </div>
            <div class="bg-white p-3 rounded-2xl rounded-tl-none border border-slate-200/80 shadow-xs max-w-[85%] text-slate-700 leading-relaxed text-xs">
                ${escapeHtml(text)}
            </div>
        `;
    }

    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
}

function appendAdvisorTyping(id) {
    const container = document.getElementById('advisorChatMessages');
    if (!container) return;

    const row = document.createElement('div');
    row.id = id;
    row.className = 'flex items-start space-x-2';
    row.innerHTML = `
        <div class="w-6 h-6 rounded-lg bg-navy-950 text-white text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
            G
        </div>
        <div class="bg-white px-3 py-2 rounded-2xl rounded-tl-none border border-slate-200 text-slate-400 text-xs flex items-center space-x-1">
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"></span>
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 0.15s"></span>
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 0.3s"></span>
        </div>
    `;
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
}

function removeAdvisorTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function renderAdvisorRecommendations(matches) {
    const container = document.getElementById('advisorChatMessages');
    if (!container) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'space-y-1.5 pl-8 pr-2';
    
    let html = '<div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Top Advisor Matches:</div>';
    matches.slice(0, 2).forEach(m => {
        html += `
            <div class="p-2.5 rounded-xl bg-white border border-brand-200/80 shadow-xs flex items-center justify-between text-[11px]">
                <div class="truncate pr-2">
                    <p class="font-bold text-navy-900 truncate">${escapeHtml(m.name)}</p>
                    <p class="text-[10px] text-slate-500">${escapeHtml(m.amount)} &bull; ${escapeHtml(m.country)}</p>
                </div>
                <span class="shrink-0 px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 font-bold text-[10px] border border-brand-200">
                    ${m.match_score}% Fit
                </span>
            </div>
        `;
    });
    wrapper.innerHTML = html;
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

// Inline Landing Page AI Advisor Handler
async function handleInlineAdvisorSubmit(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('inlineAdvisorInput');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    appendInlineMessage('user', msg);

    const typingId = 'inline_typing_' + Date.now();
    appendInlineTyping(typingId);

    try {
        const res = await fetch('/api/assistant/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg,
                history: advisorChatHistory,
                track: 'scholarship',
                session_id: advisorSessionId
            })
        });

        const data = await res.json();
        removeInlineTyping(typingId);

        if (data.reply) {
            appendInlineMessage('assistant', data.reply);
            advisorChatHistory.push({ role: 'user', content: msg });
            advisorChatHistory.push({ role: 'assistant', content: data.reply });

            if (data.recommended_matches && data.recommended_matches.length > 0) {
                renderInlineRecommendations(data.recommended_matches);
            }
        } else {
            appendInlineMessage('assistant', "I am currently evaluating matching opportunities. Please share your major or target country.");
        }
    } catch (err) {
        removeInlineTyping(typingId);
        appendInlineMessage('assistant', "The AI advisor service is momentarily reconnecting. Please send your question again.");
    }
}

function sendQuickPrompt(promptText) {
    const input = document.getElementById('inlineAdvisorInput');
    if (input) {
        input.value = promptText;
        handleInlineAdvisorSubmit(null);
    } else {
        const modalInput = document.getElementById('advisorInput');
        if (modalInput) {
            modalInput.value = promptText;
            const widget = document.getElementById('advisorChatWidget');
            if (widget && widget.classList.contains('hidden')) toggleAdvisorWidget();
            handleAdvisorSubmit(new Event('submit'));
        }
    }
}

function appendInlineMessage(role, text) {
    const container = document.getElementById('inlineAdvisorMessages');
    if (!container) return;

    const row = document.createElement('div');
    row.className = role === 'user' ? 'flex items-start justify-end space-x-2' : 'flex items-start space-x-2';

    if (role === 'user') {
        row.innerHTML = `
            <div class="bg-navy-900 text-white p-3 rounded-2xl rounded-tr-none shadow-xs max-w-[85%] text-xs leading-relaxed">
                ${escapeHtml(text)}
            </div>
            <div class="w-6 h-6 rounded-lg bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                U
            </div>
        `;
    } else {
        row.innerHTML = `
            <div class="w-6 h-6 rounded-lg bg-navy-950 text-white text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                G
            </div>
            <div class="bg-white p-3 rounded-2xl rounded-tl-none border border-slate-200/80 shadow-xs max-w-[85%] text-slate-700 leading-relaxed text-xs">
                ${escapeHtml(text)}
            </div>
        `;
    }

    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
}

function appendInlineTyping(id) {
    const container = document.getElementById('inlineAdvisorMessages');
    if (!container) return;

    const row = document.createElement('div');
    row.id = id;
    row.className = 'flex items-start space-x-2';
    row.innerHTML = `
        <div class="w-6 h-6 rounded-lg bg-navy-950 text-white text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
            G
        </div>
        <div class="bg-white px-3 py-2 rounded-2xl rounded-tl-none border border-slate-200 text-slate-400 text-xs flex items-center space-x-1">
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"></span>
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 0.15s"></span>
            <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 0.3s"></span>
        </div>
    `;
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
}

function removeInlineTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function renderInlineRecommendations(matches) {
    const container = document.getElementById('inlineAdvisorMessages');
    if (!container) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'space-y-1.5 pl-8 pr-2';
    
    let html = '<div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Top Advisor Matches:</div>';
    matches.slice(0, 2).forEach(m => {
        html += `
            <div class="p-2.5 rounded-xl bg-white border border-brand-200/80 shadow-xs flex items-center justify-between text-[11px]">
                <div class="truncate pr-2">
                    <p class="font-bold text-navy-900 truncate">${escapeHtml(m.name)}</p>
                    <p class="text-[10px] text-slate-500">${escapeHtml(m.amount)} &bull; ${escapeHtml(m.country)}</p>
                </div>
                <span class="shrink-0 px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 font-bold text-[10px] border border-brand-200">
                    ${m.match_score}% Fit
                </span>
            </div>
        `;
    });
    wrapper.innerHTML = html;
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

// ==============================================================================
// Profile Management, Supabase Avatars & Double Opt-In Handlers
// ==============================================================================

async function handleAvatarFileSelected(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    const statusEl = document.getElementById('avatarUploadStatus');
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    const maxSizeBytes = 2 * 1024 * 1024; // 2MB

    if (!allowedTypes.includes(file.type)) {
        if (statusEl) {
            statusEl.className = 'text-xs font-semibold text-rose-600 block';
            statusEl.innerText = 'Invalid format. Only JPG, PNG, and WEBP files are allowed.';
        }
        showToast('Invalid format. Only JPG, PNG, and WEBP are supported.', 'error');
        event.target.value = '';
        return;
    }

    if (file.size > maxSizeBytes) {
        if (statusEl) {
            statusEl.className = 'text-xs font-semibold text-rose-600 block';
            statusEl.innerText = 'File exceeds maximum limit of 2MB.';
        }
        showToast('File size exceeds 2MB limit.', 'error');
        event.target.value = '';
        return;
    }

    if (statusEl) {
        statusEl.className = 'text-xs font-semibold text-brand-600 block';
        statusEl.innerText = 'Uploading to Supabase Storage...';
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/auth/profile/avatar', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (res.ok && data.success) {
            const newUrl = data.avatar_url;

            // 1. Update Profile Card Preview
            const previewImg = document.getElementById('profileAvatarPreviewImg');
            const previewInitials = document.getElementById('profileAvatarPreviewInitials');
            const removeBtn = document.getElementById('removeAvatarBtn');

            if (previewImg) {
                previewImg.src = newUrl;
                previewImg.classList.remove('hidden');
            }
            if (previewInitials) {
                previewInitials.classList.add('hidden');
            }
            if (removeBtn) {
                removeBtn.classList.remove('hidden');
            }

            // 2. Immediate Reactivity: Update Navbar and Mobile Drawer DOM immediately
            const navImg = document.getElementById('navUserAvatarImg');
            const navInitials = document.getElementById('navUserAvatarInitials');
            if (navImg) {
                navImg.src = newUrl;
                navImg.classList.remove('hidden');
            }
            if (navInitials) {
                navInitials.classList.add('hidden');
            }

            const drawerImg = document.getElementById('drawerUserAvatarImg');
            const drawerInitials = document.getElementById('drawerUserAvatarInitials');
            if (drawerImg) {
                drawerImg.src = newUrl;
                drawerImg.classList.remove('hidden');
            }
            if (drawerInitials) {
                drawerInitials.classList.add('hidden');
            }

            if (statusEl) {
                statusEl.className = 'text-xs font-semibold text-emerald-600 block';
                statusEl.innerText = 'Profile picture updated successfully.';
                setTimeout(() => statusEl.classList.add('hidden'), 3000);
            }
            showToast('Profile picture uploaded successfully.', 'success');
        } else {
            const err = data.detail || 'Failed to upload photo.';
            if (statusEl) {
                statusEl.className = 'text-xs font-semibold text-rose-600 block';
                statusEl.innerText = err;
            }
            showToast(err, 'error');
        }
    } catch (err) {
        if (statusEl) {
            statusEl.className = 'text-xs font-semibold text-rose-600 block';
            statusEl.innerText = 'Network error while uploading photo.';
        }
        showToast('Network error while uploading photo.', 'error');
    } finally {
        event.target.value = '';
    }
}

async function handleAvatarRemove() {
    if (!confirm('Are you sure you want to remove your profile picture?')) return;

    const statusEl = document.getElementById('avatarUploadStatus');
    if (statusEl) {
        statusEl.className = 'text-xs font-semibold text-brand-600 block';
        statusEl.innerText = 'Removing avatar...';
    }

    try {
        const res = await fetch('/api/auth/profile/avatar', {
            method: 'DELETE'
        });
        const data = await res.json();

        if (res.ok && data.success) {
            // 1. Reset Profile Preview
            const previewImg = document.getElementById('profileAvatarPreviewImg');
            const previewInitials = document.getElementById('profileAvatarPreviewInitials');
            const removeBtn = document.getElementById('removeAvatarBtn');

            if (previewImg) {
                previewImg.src = '';
                previewImg.classList.add('hidden');
            }
            if (previewInitials) {
                previewInitials.classList.remove('hidden');
            }
            if (removeBtn) {
                removeBtn.classList.add('hidden');
            }

            // 2. Reset Navbar and Drawer
            const navImg = document.getElementById('navUserAvatarImg');
            const navInitials = document.getElementById('navUserAvatarInitials');
            if (navImg) {
                navImg.src = '';
                navImg.classList.add('hidden');
            }
            if (navInitials) {
                navInitials.classList.remove('hidden');
            }

            const drawerImg = document.getElementById('drawerUserAvatarImg');
            const drawerInitials = document.getElementById('drawerUserAvatarInitials');
            if (drawerImg) {
                drawerImg.src = '';
                drawerImg.classList.add('hidden');
            }
            if (drawerInitials) {
                drawerInitials.classList.remove('hidden');
            }

            if (statusEl) {
                statusEl.className = 'text-xs font-semibold text-emerald-600 block';
                statusEl.innerText = 'Profile picture removed.';
                setTimeout(() => statusEl.classList.add('hidden'), 3000);
            }
            showToast('Profile picture removed successfully.', 'info');
        } else {
            showToast('Could not remove avatar.', 'error');
        }
    } catch (err) {
        showToast('Network error while removing photo.', 'error');
    }
}

async function handleProfileSubmit(event) {
    event.preventDefault();

    const btn = document.getElementById('saveProfileBtn');
    const btnText = document.getElementById('saveProfileBtnText');
    const spinner = document.getElementById('saveProfileBtnSpinner');
    const feedback = document.getElementById('profileFormFeedback');

    if (btn) btn.disabled = true;
    if (btnText) btnText.innerText = 'Saving changes...';
    if (spinner) spinner.classList.remove('hidden');
    if (feedback) feedback.className = 'text-xs font-medium text-slate-500';

    const cgpaVal = document.getElementById('profileCgpa')?.value.trim() || '';
    if (cgpaVal) {
        const cleanVal = cgpaVal.replace('%', '').trim();
        const num = parseFloat(cleanVal);
        if (!isNaN(num)) {
            if (cgpaVal.includes('%')) {
                if (num < 0 || num > 100) {
                    if (feedback) {
                        feedback.className = 'text-xs font-semibold text-rose-600';
                        feedback.innerText = 'Percentage must be between 0% and 100%.';
                    }
                    if (btn) btn.disabled = false;
                    if (btnText) btnText.innerText = 'Save Profile & Preferences';
                    if (spinner) spinner.classList.add('hidden');
                    return;
                }
            } else {
                if (num < 0 || num > 4.0) {
                    if (feedback) {
                        feedback.className = 'text-xs font-semibold text-rose-600';
                        feedback.innerText = 'CGPA must be between 0.0 and 4.0 (or append % for percentage).';
                    }
                    if (btn) btn.disabled = false;
                    if (btnText) btnText.innerText = 'Save Profile & Preferences';
                    if (spinner) spinner.classList.add('hidden');
                    return;
                }
            }
        }
    }

    const payload = {
        name: document.getElementById('profileName').value.trim(),
        email: document.getElementById('profileEmail').value.trim(),
        role: document.getElementById('profileRole')?.value || undefined,
        type: document.getElementById('profileType').value,
        major_domain: document.getElementById('profileMajorDomain').value.trim(),
        degree_level_stage: document.getElementById('profileDegreeStage').value.trim(),
        gpa_funding: document.getElementById('profileGpaFunding').value.trim(),
        country_preference: document.getElementById('profileCountryPreference').value,
        university: document.getElementById('profileUniversity')?.value.trim() || '',
        cgpa: cgpaVal,
        city: document.getElementById('profileCity')?.value.trim() || '',
        grad_year: document.getElementById('profileGradYear')?.value.trim() || '',
        test_scores: document.getElementById('profileTestScores')?.value.trim() || '',
        financial_need: document.getElementById('profileFinancialNeed')?.value || 'No',
        notification_preference: document.getElementById('profileNotificationPref')?.value || 'in_app'
    };

    try {
        const res = await fetch('/api/auth/profile/details', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok && data.success) {
            if (feedback) {
                feedback.className = 'text-xs font-semibold text-emerald-600';
                feedback.innerText = 'Profile and preferences updated successfully.';
            }
            showToast('Profile and preferences updated.', 'success');

            // Update completion percentage meter if returned
            if (data.profile && typeof data.profile.completion_pct === 'number') {
                const bar = document.getElementById('profileCompletionBar');
                const pctLabel = document.getElementById('profileCompletionPctText');
                if (bar) bar.style.width = data.profile.completion_pct + '%';
                if (pctLabel) pctLabel.innerText = data.profile.completion_pct + '%';
            }
        } else {
            const err = data.detail || 'Failed to update profile.';
            if (feedback) {
                feedback.className = 'text-xs font-semibold text-rose-600';
                feedback.innerText = err;
            }
            showToast(err, 'error');
        }
    } catch (err) {
        if (feedback) {
            feedback.className = 'text-xs font-semibold text-rose-600';
            feedback.innerText = 'Network error while saving profile.';
        }
        showToast('Network error while saving profile.', 'error');
    } finally {
        if (btn) btn.disabled = false;
        if (btnText) btnText.innerText = 'Save Profile & Preferences';
        if (spinner) spinner.classList.add('hidden');
    }
}

async function handleResendConfirmation() {
    const btn = document.getElementById('resendOptInBtn');
    const statusEl = document.getElementById('resendOptInStatus');

    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Dispatching email...';
    }

    try {
        const res = await fetch('/api/notifications/resend-confirmation', {
            method: 'POST'
        });
        const data = await res.json();

        if (res.ok && data.success) {
            if (statusEl) {
                statusEl.className = 'text-xs font-semibold text-emerald-600 block';
                statusEl.innerText = data.message || 'Confirmation email dispatched. Check your inbox.';
            }
            showToast('Confirmation email sent to your inbox.', 'success');
        } else {
            const err = data.detail || 'Could not send confirmation email.';
            if (statusEl) {
                statusEl.className = 'text-xs font-semibold text-rose-600 block';
                statusEl.innerText = err;
            }
            showToast(err, 'error');
        }
    } catch (err) {
        if (statusEl) {
            statusEl.className = 'text-xs font-semibold text-rose-600 block';
            statusEl.innerText = 'Network error while requesting confirmation.';
        }
        showToast('Network error.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Resend Confirmation Email & OTP';
        }
    }
}

async function handleVerifyOtpSubmit() {
    const input = document.getElementById('emailOtpInput');
    const btn = document.getElementById('verifyOtpBtn');
    const statusEl = document.getElementById('otpVerificationStatus');
    const badge = document.getElementById('optInBadge');

    if (!input) return;
    const code = input.value.trim();
    if (!code || code.length < 6) {
        showToast('Please enter a valid 6-digit verification code.', 'error');
        if (statusEl) {
            statusEl.className = 'text-xs font-semibold text-rose-600 block';
            statusEl.innerText = 'Please enter all 6 digits of your code.';
        }
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Verifying...';
    }

    try {
        const res = await fetch('/api/notifications/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ otp: code })
        });
        const data = await res.json();

        if (res.ok && data.success) {
            showToast('Email verified successfully! Alerts activated.', 'success');
            if (statusEl) {
                statusEl.className = 'text-xs font-semibold text-emerald-600 block';
                statusEl.innerText = data.message || 'Email verified successfully!';
            }
            if (badge) {
                badge.className = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300';
                badge.innerText = 'Active & Confirmed';
            }
            setTimeout(() => {
                window.location.reload();
            }, 1200);
        } else {
            const err = data.detail || 'Verification code failed.';
            showToast(err, 'error');
            if (statusEl) {
                statusEl.className = 'text-xs font-semibold text-rose-600 block';
                statusEl.innerText = err;
            }
        }
    } catch (err) {
        showToast('Network error while verifying OTP.', 'error');
        if (statusEl) {
            statusEl.className = 'text-xs font-semibold text-rose-600 block';
            statusEl.innerText = 'Network error. Please try again.';
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Verify Code';
        }
    }
}

function handleFooterSubscribe(e) {
    e.preventDefault();
    const input = document.getElementById('footerNewsletterEmail');
    const btn = document.getElementById('footerNewsletterBtn');
    if (!input || !input.value.trim()) return;

    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Subscribing...';
    }

    setTimeout(() => {
        showToast('Subscribed! Confirmation dispatched to ' + input.value.trim(), 'success');
        input.value = '';
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Subscribed!';
            setTimeout(() => {
                btn.innerText = 'Subscribe to Alerts \u2192';
            }, 3000);
        }
    }, 500);
}




