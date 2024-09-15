
async function getData() {
    const url = "/oembed?url=" + encodeURI("https://open.spotify.com/playlist/5xgYeWxF4lKIeqOsSjfwXt?si=7ae1153ef3b64040");
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Response status: ${response.status}`);
      }
  
      const json = await response.json();
      console.log(json.html);
      const div = document.getElementById('oembed');
      div.innerHTML = json.html;
    } catch (error) {
      console.error(error.message);
    }
  }

getData()