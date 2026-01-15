// camera_mark.js
const startMarkBtn = document.getElementById('startMarkBtn')
const stopMarkBtn = document.getElementById('stopMarkBtn')
const markVideo = document.getElementById('markVideo')
const markStatus = document.getElementById('markStatus')
const recognizedList = document.getElementById('recognizedList')
const clockEl = document.getElementById('liveClock')
const periodEl = document.getElementById('activePeriodDisplay')

let markStream = null
let markInterval = null
let isProcessing = false

// 1. LIVE CLOCK & DYNAMIC PERIOD UI LOGIC
async function updateKioskUI() {
  const now = new Date()
  clockEl.innerText = now.toLocaleTimeString()

  try {
    // Fetch the active period name from the server based on the database routine
    const res = await fetch('/get_active_period_name')
    const data = await res.json()

    // Update the Period Display card
    if (data.period === 'Free Period') {
      periodEl.innerText = 'Free Period'
      periodEl.className = 'text-xl font-bold text-gray-500'
    } else {
      periodEl.innerText = data.period // Displays the name set in /set_routine
      periodEl.className = 'text-xl font-bold text-blue-400'
    }
  } catch (e) {
    console.error('Routine fetch error:', e)
    periodEl.innerText = 'Offline'
  }
}

// Keep the clock ticking and period checking every second
setInterval(updateKioskUI, 1000)
updateKioskUI()

// 2. AUTOMATED RECOGNITION LOGIC
startMarkBtn.addEventListener('click', async () => {
  startMarkBtn.disabled = true
  stopMarkBtn.disabled = false
  try {
    markStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
    })
    markVideo.srcObject = markStream
    await markVideo.play()
    markStatus.innerText = 'Scanning door...'

    // Auto-scan every 1.5 seconds
    markInterval = setInterval(captureAndRecognize, 1500)
  } catch (err) {
    alert('Camera error: ' + err.message)
    startMarkBtn.disabled = false
  }
})

async function captureAndRecognize() {
  if (isProcessing) return // Prevent overlapping network requests
  isProcessing = true

  const canvas = document.createElement('canvas')
  canvas.width = markVideo.videoWidth || 640
  canvas.height = markVideo.videoHeight || 480
  const ctx = canvas.getContext('2d')
  ctx.drawImage(markVideo, 0, 0, canvas.width, canvas.height)

  const blob = await new Promise((r) => canvas.toBlob(r, 'image/jpeg', 0.85))
  const fd = new FormData()
  fd.append('image', blob, 'snap.jpg')

  try {
    const res = await fetch('/recognize_face', { method: 'POST', body: fd })
    const j = await res.json()

    if (j.recognized) {
      if (j.already_logged) {
        // Visual feedback for students already marked for this period
        markStatus.innerHTML = `<span class="text-yellow-500">Already Marked: ${j.name}</span>`
      } else {
        // Visual feedback for new successful attendance
        markStatus.innerHTML = `<span class="text-green-500 font-bold">Welcome, ${j.name}!</span>`
        addToList(j)
      }
      // Reset status text after 3 seconds for the next student
      setTimeout(() => {
        if (markInterval) markStatus.innerText = 'Scanning...'
      }, 3000)
    }
  } catch (err) {
    console.error('Fetch error:', err)
  } finally {
    isProcessing = false
  }
}

function addToList(j) {
  // Play success beep
  const sound = document.getElementById('successSound')
  if (sound) {
    sound.currentTime = 0
    sound
      .play()
      .catch((e) =>
        console.log("Audio play blocked. Click 'Start Kiosk' first.")
      )
  }

  if (recognizedList.innerHTML.includes('No students detected'))
    recognizedList.innerHTML = ''

  const li = document.createElement('li')
  li.className =
    'p-4 flex flex-col border-b border-gray-800 bg-blue-900/10 animate-pulse'
  li.innerHTML = `
    <div class="flex justify-between items-center">
      <span class="text-white font-bold">${j.name}</span>
      <span class="text-[10px] text-gray-400">${new Date().toLocaleTimeString()}</span>
    </div>
    <div class="text-[11px] text-gray-500 italic">${j.period}</div>
  `
  recognizedList.prepend(li)
}

stopMarkBtn.addEventListener('click', () => {
  clearInterval(markInterval)
  if (markStream) markStream.getTracks().forEach((t) => t.stop())
  startMarkBtn.disabled = false
  stopMarkBtn.disabled = true
  markStatus.innerText = 'Stopped'
})
