// camera_add_student.js
const saveInfoBtn = document.getElementById('saveInfoBtn')
const startCaptureBtn = document.getElementById('startCaptureBtn')
const addStudentBtn = document.getElementById('addStudentBtn')
const video = document.getElementById('video')
const captureStatus = document.getElementById('captureStatus')
const progressBar = document.getElementById('progressBar')

let student_id = null
let captured = 0
const maxImages = 50
let images = []
let stream = null

document.getElementById('studentForm').addEventListener('submit', async (e) => {
  e.preventDefault()

  // Disable button to prevent double clicks
  saveInfoBtn.disabled = true
  saveInfoBtn.innerText = 'Saving...'

  const fd = new FormData(e.target)

  try {
    const res = await fetch('/add_student', { method: 'POST', body: fd })

    if (!res.ok) {
      const errorData = await res.json()
      console.error('Server Error:', errorData)
      alert(
        'Failed to save student info: ' + (errorData.error || 'Unknown error')
      )
      saveInfoBtn.disabled = false
      saveInfoBtn.innerText = 'Save Info'
      return
    }

    const j = await res.json()
    student_id = j.student_id
    alert("Student info saved! Now click 'Start Capture'.")

    // UI Updates
    startCaptureBtn.disabled = false
    saveInfoBtn.classList.add('opacity-50', 'cursor-not-allowed')
    saveInfoBtn.innerText = 'Saved ✓'
  } catch (err) {
    console.error('Fetch Error:', err)
    alert('Connection error. Is the server running?')
    saveInfoBtn.disabled = false
  }
})

startCaptureBtn.addEventListener('click', async () => {
  startCaptureBtn.disabled = true
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
    })
    video.srcObject = stream
    await video.play()
    captureImagesLoop()
  } catch (err) {
    alert('Camera access error: ' + err.message)
    startCaptureBtn.disabled = false
  }
})

async function captureImagesLoop() {
  const canvas = document.createElement('canvas')
  // Wait for video metadata to get correct dimensions
  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480
  const ctx = canvas.getContext('2d')

  while (captured < maxImages) {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise((res) =>
      canvas.toBlob(res, 'image/jpeg', 0.8)
    )
    images.push(blob)
    captured++

    captureStatus.innerHTML = `Captured <span class="text-blue-400 font-bold">${captured}</span> / ${maxImages}`
    progressBar.style.width = `${(captured / maxImages) * 100}%`

    await new Promise((r) => setTimeout(r, 150)) // Faster capture (150ms)
  }

  // UPLOAD
  captureStatus.innerText = 'Uploading faces... Please wait.'
  const form = new FormData()
  form.append('student_id', student_id)
  images.forEach((b, i) => form.append('images[]', b, `img_${i}.jpg`))

  const resp = await fetch('/upload_face', { method: 'POST', body: form })
  if (resp.ok) {
    alert('Facial data uploaded successfully!')
    addStudentBtn.disabled = false
    captureStatus.innerText = 'Face Capture Complete ✓'
  } else {
    alert('Upload failed. Try capturing again.')
    captured = 0
    images = []
    startCaptureBtn.disabled = false
  }

  if (stream) stream.getTracks().forEach((t) => t.stop())
}

addStudentBtn.addEventListener('click', () => {
  window.location.href = '/'
})
