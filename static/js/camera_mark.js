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
// Memory to store students already marked in the current session
let markedInSession = new Set()

// 1. LIVE CLOCK & DYNAMIC PERIOD UI LOGIC
async function updateKioskUI() {
  const now = new Date()
  clockEl.innerText = now.toLocaleTimeString()

  try {
    const res = await fetch('/get_active_period_name')
    const data = await res.json()

    if (data.period === 'Free Period') {
      periodEl.innerText = 'Free Period'
      periodEl.className = 'text-xl font-bold text-gray-500'
      // Clear session memory when moving to a free period
      markedInSession.clear()
    } else {
      periodEl.innerText = data.period
      periodEl.className = 'text-xl font-bold text-purple-400'
    }
  } catch (e) {
    console.error('Routine fetch error:', e)
    periodEl.innerText = 'Offline'
  }
}

setInterval(updateKioskUI, 1000)
updateKioskUI()

// 2. AUTOMATED RECOGNITION LOGIC
startMarkBtn.addEventListener('click', async () => {
  startMarkBtn.disabled = true
  stopMarkBtn.disabled = false
  stopMarkBtn.className =
    'px-8 py-3 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-black text-sm transition-all'

  try {
    markStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
    })
    markVideo.srcObject = markStream
    await markVideo.play()
    markStatus.innerText = 'Scanning signatures...'
    markInterval = setInterval(captureAndRecognize, 1500)
  } catch (err) {
    alert('Camera error: ' + err.message)
    startMarkBtn.disabled = false
  }
})

async function captureAndRecognize() {
  if (isProcessing) return
  isProcessing = true

  const canvas = document.createElement('canvas')
  canvas.width = markVideo.videoWidth || 640
  canvas.height = markVideo.videoHeight || 480
  canvas.getContext('2d').drawImage(markVideo, 0, 0)

  const blob = await new Promise((r) => canvas.toBlob(r, 'image/jpeg', 0.85))
  const fd = new FormData()
  fd.append('image', blob, 'snap.jpg')

  // FIXED: Removed the document.getElementById call for the missing selector
  // Sending a default ID so the backend recognize_face route still receives the key
  fd.append('camera_id', 'default_unit')

  try {
    const res = await fetch('/recognize_face', { method: 'POST', body: fd })
    const j = await res.json()

    if (j.error) {
      markStatus.innerHTML = `<span class="text-red-500 font-bold">${j.error}</span>`
    } else if (j.recognized) {
      // LOGIC: Check if student is already in our session memory
      if (markedInSession.has(j.name)) {
        markStatus.innerHTML = `<span class="text-zinc-500 italic">Verified: ${j.name}</span>`
      } else {
        // Handle new recognition or student already marked in DB today
        if (j.already_logged) {
          markStatus.innerHTML = `<span class="text-yellow-500 font-bold">${j.name} (Already Marked Today)</span>`
          markedInSession.add(j.name) // Add to session memory to stop re-processing
        } else {
          markStatus.innerHTML = `<span class="text-emerald-500 font-black">Welcome, ${j.name}!</span>`
          addToList(j)
          markedInSession.add(j.name) // Add to session memory
        }
      }

      // Reset status text briefly after 2 seconds
      setTimeout(() => {
        if (markInterval) markStatus.innerText = 'Scanning signatures...'
      }, 2000)
    }
  } catch (err) {
    console.error('Fetch error:', err)
  } finally {
    isProcessing = false
  }
}

function addToList(j) {
  const sound = document.getElementById('successSound')
  if (sound) {
    sound.currentTime = 0
    sound.play().catch((e) => console.log('Audio play blocked.'))
  }

  if (
    recognizedList.innerHTML.includes('Waiting for biometric detection') ||
    recognizedList.innerHTML.includes('No students detected')
  ) {
    recognizedList.innerHTML = ''
  }

  const li = document.createElement('li')
  li.className =
    'p-5 flex flex-col border-b border-white/5 bg-blue-600/5 transition-all animate-pulse'
  li.innerHTML = `
    <div class="flex justify-between items-center mb-1">
      <span class="text-white font-bold tracking-tight">${j.name}</span>
      <span class="text-[10px] font-mono text-zinc-500">${new Date().toLocaleTimeString('en-GB')}</span>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-[10px] text-zinc-400 uppercase font-black tracking-widest">${j.period}</span>
      <span class="text-[9px] text-emerald-500 font-bold">VERIFIED</span>
    </div>
  `
  recognizedList.prepend(li)
}

stopMarkBtn.addEventListener('click', () => {
  clearInterval(markInterval)
  markInterval = null
  markedInSession.clear() // Clear memory when stopping kiosk
  if (markStream) markStream.getTracks().forEach((t) => t.stop())
  startMarkBtn.disabled = false
  stopMarkBtn.disabled = true
  stopMarkBtn.className =
    'px-8 py-3 bg-zinc-800 text-zinc-500 rounded-2xl font-black text-sm cursor-not-allowed border border-white/5'
  markStatus.innerText = 'System Stopped'
})
