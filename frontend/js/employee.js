async function initEmployee() {
    document.getElementById('templateForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        console.log("submit")
    }); //On submit logic here

    document.getElementById('fillSampleButton')?.addEventListener('click', () => {console.log("sample")}); //Sample button logic here
}
