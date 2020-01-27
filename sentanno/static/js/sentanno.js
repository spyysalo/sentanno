/* hotkeys (TODO: make configurable) */

var spinCounter = 0;

function updateSpinner() {
    spinner = document.getElementById("spinner");
    if (spinCounter > 0) {
	spinner.style.display = 'inline';
    } else {
	spinner.style.display = 'none';
    }
}

// https://stackoverflow.com/a/6234804
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

var allCandidatesLabeled = false;

function updatePicks() {
    var candidates = document.getElementsByClassName("pa-candidate");
    var accepted = METADATA['accepted'] || [];
    var rejected = METADATA['rejected'] || [];
    allCandidatesLabeled = true;
    for (let i=0; i<candidates.length; i++) {
	let element = candidates[i];
	let cid = element.id.replace("candidate-", "");
	if (accepted.includes(cid)) {
	    element.classList.add("accepted");
	    element.classList.remove("rejected");
	    element.classList.remove("incomplete");
	} else if(rejected.includes(cid)) {
	    element.classList.add("rejected");
	    element.classList.remove("accepted");
	    element.classList.remove("incomplete");
	} else {
	    element.classList.add("incomplete");
	    element.classList.remove("rejected");
	    element.classList.remove("accepted");
	    allCandidatesLabeled = false;
	}
    }
}

function updateKeywords() {
    var kwRow = document.getElementById("keywords-row");
    var keywords = METADATA["keywords"].split(",");
    for (var i=0; i<keywords.length; i++) {
	keywords[i] = keywords[i].toLowerCase().trim();
    }
    keywords = Array.from(new Set(keywords));
    keywords.sort();
    var kwSpans = [];
    for (var i=0; i<keywords.length; i++) {
	var k = keywords[i]
	if (k) {
	    kwSpans.push('<span class="keyword-span">'+escapeHtml(k)+'</span>');
	}
    }
    kwRow.innerHTML = kwSpans.join("");
}

function spinUp() {
    spinCounter++;
    updateSpinner();
}

function spinDown() {
    spinCounter--;
    updateSpinner();
}

function isAbsolute(url) {
    var re = new RegExp('^[a-z]+://', 'i');
    return re.test(url);
}

function makeUrl(url, params) {
    // Adapted from https://fetch.spec.whatwg.org/#fetch-api
    if (isAbsolute(url)) {
	url = new URL(url);
    } else {
	url = new URL(url, window.location.origin);
    }
    Object.keys(params).forEach(
	key => url.searchParams.append(key, params[key])
    );
    return url;
}

async function pickCandidate(pick) {
    spinUp();
    var url = makeUrl(PICK_ANNO_URL, { "choice":  pick });
    var response = await fetch(url);
    var data = await response.json();
    METADATA['accepted'] = data['accepted'];
    METADATA['rejected'] = data['rejected'];
    updatePicks();
    spinDown();
    return data;
}

async function saveKeywords() {
    spinUp();
    var textInput = document.getElementById("keyword-input");
    var keywords = textInput.value;
    var url = makeUrl(SAVE_KEYWORDS_URL, { "keywords":  keywords });
    var response = await fetch(url);
    var data = await response.json();
    METADATA["keywords"] = data["keywords"];
    updateKeywords();
    spinDown();
}

var keywordTimeout;    // Don't save on every keypress

function keywordsChanged() {
    var textInput = document.getElementById("keyword-input");
    var keywords = textInput.value;
    clearTimeout(keywordTimeout);
    keywordTimeout = setTimeout(function() {
	saveKeywords();
    }, 10); // , 1000); // 1sec
}

/* set up events */

var textInputFocused = false;

document.addEventListener('keydown', function(event) {
    if (textInputFocused) {
	// No hotkeys when in text input, but blur on Enter
	if (event.key == 'Enter') {
	    document.getElementById("keyword-input").blur();
	}
    }
    else if (event.key in HOTKEYS) {
	// HOTKEYS defined in config.py
	let pick = HOTKEYS[event.key];
	pickCandidate(pick);
	event.preventDefault();
	event.stopPropagation();
    }
    else if (event.key == 'Enter' || event.key == 'ArrowRight') {
	// TODO make configurable
	let link = document.getElementById("nav-next-link");
	if (link) {
	    if (allCandidatesLabeled) {
		link.click();
	    } else {
		if (confirm("Are you sure you want to leave\nthis document without a judgment?")) {
		    link.click();
		}
	    }
	}
	event.preventDefault();
	event.stopPropagation();
    }
    else if (event.key == 'ArrowLeft') {
	let link = document.getElementById("nav-prev-link");
	if (link) {
	    link.click();
	}
	event.preventDefault();
	event.stopPropagation();
    }
});

function load() {
    var candidates = document.getElementsByClassName("pa-candidate");
    for (let i=0; i<candidates.length; i++) {
	let element = candidates[i];
	let cid = element.id.replace("candidate-", "");
	element.onclick = function() {
	    pickCandidate(cid);
	};
    }
    var textInput = document.getElementById("keyword-input");
    textInput.addEventListener('input', keywordsChanged);
    textInput.addEventListener('propertychange', keywordsChanged); // IE <= 8
    textInput.addEventListener('focus', function() { textInputFocused = true });
    textInput.addEventListener('blur', function() { textInputFocused = false });
    updatePicks();
    updateKeywords();
}
