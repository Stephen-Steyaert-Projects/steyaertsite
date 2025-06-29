function redirectToSearch(form) {
    const input = document.getElementById('searchTitle');
    const title = input.value.trim();
    if (!title) return false;
    const encodedTitle = encodeURIComponent(title);
    window.location.href = `/search/${encodedTitle}/`;
    return false; // prevent form submission
}
