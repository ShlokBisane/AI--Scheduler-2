/**
 * Profile Module — Personal profile page that opens in place of chat.
 * Helps AI understand user context for smarter scheduling.
 * Now includes class-based session detection hints.
 */

const Profile = (() => {

    function init() {
        // Profile link in sidebar
        const profileBtn = document.getElementById('profile-btn');
        if (profileBtn) {
            profileBtn.addEventListener('click', show);
        }

        // Class field detection
        const classInput = document.getElementById('profile-class');
        if (classInput) {
            classInput.addEventListener('input', () => {
                updateClassHint(classInput.value);
            });
        }
    }

    async function show() {
        // Hide chat area, show profile page
        const chatArea = document.getElementById('chat-area');
        const profilePage = document.getElementById('profile-page');
        const titleDisplay = document.getElementById('chat-title-display');

        if (chatArea) chatArea.style.display = 'none';
        if (profilePage) {
            profilePage.style.display = 'flex';
            titleDisplay.textContent = 'My Profile';
        }

        // Deselect chat items
        document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));

        // Load existing profile
        try {
            const data = await Api.getProfile();
            const profile = data.profile || {};
            fillForm(profile);
        } catch (err) {
            // Fresh profile
        }

        // Setup save handler (remove old listener to prevent duplicates)
        const saveBtn = document.getElementById('profile-save-btn');
        if (saveBtn) {
            const newBtn = saveBtn.cloneNode(true);
            saveBtn.parentNode.replaceChild(newBtn, saveBtn);
            newBtn.addEventListener('click', save);
        }
    }

    function fillForm(profile) {
        const fields = [
            'profile-name', 'profile-class', 'profile-board', 
            'profile-subjects', 'profile-daily-hours', 'profile-slots',
            'profile-sleep', 'profile-wake', 'profile-tuition',
            'profile-coaching', 'profile-college', 'profile-language'
        ];

        const keys = [
            'name', 'class_course', 'board_university',
            'subjects', 'daily_study_hours', 'preferred_slots',
            'sleep_time', 'wake_time', 'tuition_timings',
            'coaching_timings', 'college_timings', 'preferred_language'
        ];

        fields.forEach((fieldId, i) => {
            const el = document.getElementById(fieldId);
            if (el && profile[keys[i]]) {
                el.value = profile[keys[i]];
            }
        });

        // User type (student/teacher)
        const typeSelect = document.getElementById('profile-type');
        if (typeSelect && profile.user_type) {
            typeSelect.value = profile.user_type;
        }

        // Can study long
        const longStudy = document.getElementById('profile-long-study');
        if (longStudy && profile.can_study_long) {
            longStudy.value = profile.can_study_long;
        }

        // Update class hint
        if (profile.class_course) {
            updateClassHint(profile.class_course);
        }
    }

    function updateClassHint(value) {
        const hint = document.getElementById('class-hint');
        if (!hint) return;

        if (!value || !value.trim()) {
            hint.textContent = '';
            hint.className = 'profile-hint';
            return;
        }

        const text = value.toLowerCase().trim();
        let message = '';
        let type = 'info';

        // University detection
        const uniKeywords = ['btech', 'b.tech', 'mtech', 'mbbs', 'bds', 'bca', 'mca',
                            'bba', 'mba', 'bsc', 'msc', 'ba', 'ma', 'bcom', 'mcom',
                            'university', 'college', 'engineering', 'medical', 'law',
                            'llb', 'phd', 'diploma', 'polytechnic'];

        for (const kw of uniKeywords) {
            if (text.includes(kw)) {
                message = '🎓 University level → 50min sessions, 10min breaks';
                type = 'info';
                break;
            }
        }

        if (!message) {
            // Extract class number
            const classMatch = text.match(/(?:class\s*|grade\s*|std\s*)?(\d+)/);
            if (classMatch) {
                const num = parseInt(classMatch[1]);
                if (num >= 1 && num <= 4) {
                    message = '📚 Class 1-4 → 25-30min sessions, 5-10min breaks';
                } else if (num >= 5 && num <= 8) {
                    message = '📖 Class 5-8 → 30-35min sessions, 5-10min breaks';
                } else if (num === 10 || num === 12) {
                    message = `⚠️ Class ${num} (BOARD EXAM) → 35-45min sessions, extra revision`;
                    type = 'warning';
                } else if (num >= 9 && num <= 12) {
                    message = '📝 Class 9-12 → 35-45min sessions, 5-10min breaks';
                }
            }
        }

        hint.textContent = message;
        hint.className = `profile-hint ${type}`;
    }

    async function save() {
        const profileData = {
            name: getVal('profile-name'),
            user_type: getVal('profile-type') || 'student',
            class_course: getVal('profile-class'),
            board_university: getVal('profile-board'),
            subjects: getVal('profile-subjects'),
            daily_study_hours: getVal('profile-daily-hours'),
            preferred_slots: getVal('profile-slots'),
            sleep_time: getVal('profile-sleep'),
            wake_time: getVal('profile-wake'),
            tuition_timings: getVal('profile-tuition'),
            coaching_timings: getVal('profile-coaching'),
            college_timings: getVal('profile-college'),
            can_study_long: getVal('profile-long-study'),
            preferred_language: getVal('profile-language'),
        };

        try {
            await Api.saveProfile(profileData);
            showToast('Profile saved! AI will use this context for better scheduling.', 'success');
        } catch (err) {
            showToast('Failed to save profile: ' + err.message);
        }
    }

    function getVal(id) {
        const el = document.getElementById(id);
        return el ? el.value.trim() : '';
    }

    function hide() {
        const chatArea = document.getElementById('chat-area');
        const profilePage = document.getElementById('profile-page');
        if (chatArea) chatArea.style.display = 'flex';
        if (profilePage) profilePage.style.display = 'none';
    }

    return { init, show, hide };
})();
