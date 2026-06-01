# extractor.py
# The actual scraping/extraction logic — JavaScript that runs inside the browser
# This is the "bs4 equivalent" — it parses the page content and extracts metrics

EXTRACT_JS = """
function parseNum(text) {
    if (!text) return null;
    text = text.trim();
    
    // Handle K/M/B suffixes (e.g., "17M", "2.5K")
    var suffixMatch = text.match(/^([\\d.,]+)\\s*([KMB])$/i);
    if (suffixMatch) {
        // Convert any comma to dot for parsing (e.g. 1,5M -> 1.5)
        var numStr = suffixMatch[1].replace(/,/g, '.');
        var num = parseFloat(numStr);
        var mult = { K: 1000, M: 1000000, B: 1000000000 }[suffixMatch[2].toUpperCase()];
        return num * mult;
    }
    
    // Standard raw numbers are integers (posts, followers). 
    // We can safely remove all commas and dots.
    var cleanText = text.replace(/[.,]/g, '');
    var res = parseInt(cleanText, 10);
    return isNaN(res) ? null : res;
}

function findByLabel(labelText) {
    var allEls = document.querySelectorAll('*');
    for (var i = 0; i < allEls.length; i++) {
        var el = allEls[i];
        var t = el.innerText ? el.innerText.trim().toLowerCase() : '';
        if (t === labelText || t === labelText + 's') {
            var parent = el.parentElement;
            if (!parent) continue;
            var children = parent.children;
            for (var j = 0; j < children.length; j++) {
                var sib = children[j];
                if (sib === el) continue;
                var sibText = sib.innerText ? sib.innerText.trim() : '';
                if (sibText && /^[\\d.,]+[KMB]?$/.test(sibText)) {
                    return sibText;
                }
            }
        }
    }
    return null;
}

function findBeforeLabel(label) {
    var allText = document.body.innerText;
    var regex = new RegExp('([\\\\d.,]+[KMB]?)\\\\s*\\\\n\\\\s*' + label, 'i');
    var match = allText.match(regex);
    return match ? match[1] : null;
}

function findDailyGrowth() {
    var allText = document.body.innerText;
    var match = allText.match(/([-+]?[\\d.,]+)\\s*\\n\\s*Average followers per day/i);
    return match ? parseNum(match[1]) : null;
}

function wrap(val) {
    if (val === null || val === undefined || isNaN(val)) {
        return { value: null, status: "missing" };
    }
    return { value: val, status: "ok" };
}

function extractProfile() {
    var followersRaw = findBeforeLabel('Followers');
    var followers = parseNum(followersRaw);
    var followingRaw = findByLabel('following');
    var following = parseNum(followingRaw);
    var postsRaw = findByLabel('post');
    var postsCount = parseNum(postsRaw);
    var username = window.location.pathname.split('/').pop();
    
    return {
        username: { value: username, status: "ok" },
        followers: wrap(followers),
        following: wrap(following),
        posts_count: wrap(postsCount)
    };
}

function extractEngagement(followers) {
    var avgLikesRaw = findByLabel('avg like') || findBeforeLabel('Avg likes');
    var avgLikes = parseNum(avgLikesRaw);
    var avgCommentsRaw = findByLabel('avg comment') || findBeforeLabel('Avg comments');
    var avgComments = parseNum(avgCommentsRaw);
    
    var engagementRate = null;
    if (followers && followers > 0 && avgLikes !== null && avgComments !== null) {
        engagementRate = Math.round(((avgLikes + avgComments) / followers) * 10000) / 100;
    }
    
    return {
        avg_likes: wrap(avgLikes),
        avg_comments: wrap(avgComments),
        engagement_rate: wrap(engagementRate)
    };
}

function extractGrowth(followers) {
    var dailyGrowthRaw = findDailyGrowth();
    var growthRate = null;
    if (followers && followers > 0 && dailyGrowthRaw !== null) {
        growthRate = Math.round((dailyGrowthRaw * 30 / followers) * 1000) / 10;
    }
    return {
        daily_growth: wrap(dailyGrowthRaw),
        growth_rate: wrap(growthRate)
    };
}

function extractHashtags() {
    var allText = document.body.innerText;
    var match = allText.match(/Top hashtags.*?\\n((?:#[\\w]+\\s*)+)/is);
    var tags = [];
    if (match && match[1]) {
        tags = match[1].split(/[\\s\\n]+/).filter(function(t) { return t.startsWith('#'); });
    }
    if (tags.length > 0) {
        return { top_hashtags: { value: tags, status: "ok" } };
    }
    return { top_hashtags: { value: null, status: "missing" } };
}

var profile = extractProfile();
var engagement = extractEngagement(profile.followers.value);
var growth = extractGrowth(profile.followers.value);
var hashtags = extractHashtags();

return {
    profile_metrics: profile,
    engagement_metrics: engagement,
    growth_metrics: growth,
    hashtag_metrics: hashtags,
    authenticity_metrics: {
        authenticity_score: { value: null, status: "unavailable" } // Site locks this behind login now
    }
};
"""

def validate_result(data: dict) -> bool:
    """
    Check if the extracted data looks valid structurally.
    """
    if not data or not isinstance(data, dict):
        return False
    
    prof = data.get("profile_metrics", {})
    followers_obj = prof.get("followers", {})
    val = followers_obj.get("value")
    
    if val is None or val == 0:
        return False
        
    return True

def clean_result(data: dict, username: str) -> dict:
    """
    Post-process the nested structure.
    Override username from function argument.
    """
    if "profile_metrics" in data:
        if "username" in data["profile_metrics"]:
            data["profile_metrics"]["username"]["value"] = username
            data["profile_metrics"]["username"]["status"] = "ok"
    return data
