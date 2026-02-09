// camera_add_student.js
const saveInfoBtn = document.getElementById('saveInfoBtn')
const startCaptureBtn = document.getElementById('startCaptureBtn')
const addStudentBtn = document.getElementById('addStudentBtn')
const video = document.getElementById('video')
const captureStatus = document.getElementById('captureStatus')
const progressBar = document.getElementById('progressBar')
const progressText = document.getElementById('progressText') // Added for percentage text

let student_id = null
let captured = 0
const maxImages = 50
let images = []
let stream = null

// 1. SAVE STUDENT INFO
document.getElementById('studentForm').addEventListener('submit', async (e) => {
  e.preventDefault()

  saveInfoBtn.disabled = true
  saveInfoBtn.innerText = 'Saving...'

  const fd = new FormData(e.target)

  try {
    const res = await fetch('/add_student', { method: 'POST', body: fd })
    const j = await res.json()

    if (res.ok && j.student_id) {
      student_id = j.student_id
      alert('Profile Created! You can now start face capture.')

      // UI Transition
      startCaptureBtn.disabled = false
      saveInfoBtn.innerText = 'Profile Saved ✓'
      saveInfoBtn.classList.add('opacity-50', 'cursor-not-allowed')
    } else {
      throw new Error(j.error || 'Database insertion failed')
    }
  } catch (err) {
    console.error('Error:', err)
    alert('Error saving info: ' + err.message)
    saveInfoBtn.disabled = false
    saveInfoBtn.innerText = 'Save Profile'
  }
})

// 2. START CAMERA
startCaptureBtn.addEventListener('click', async () => {
  if (!student_id) {
    alert('Please save student info first!')
    return
  }

  startCaptureBtn.disabled = true
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
    })
    video.srcObject = stream

    // Wait for video to be ready before starting loop
    video.onloadedmetadata = () => {
      video.play()
      captureImagesLoop()
    }
  } catch (err) {
    alert('Camera access error: ' + err.message)
    startCaptureBtn.disabled = false
  }
})

// 3. CAPTURE LOOP
async function captureImagesLoop() {
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')

  while (captured < maxImages) {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    const blob = await new Promise((res) =>
      canvas.toBlob(res, 'image/jpeg', 0.8),
    )
    images.push(blob)
    captured++

    // Update Progress UI
    const percent = Math.round((captured / maxImages) * 100)
    captureStatus.innerHTML = `Signatures: <span class="text-blue-400 font-bold">${captured}</span> / ${maxImages}`
    if (progressBar) progressBar.style.width = `${percent}%`
    if (progressText) progressText.innerText = `${percent}%`

    await new Promise((r) => setTimeout(r, 100)) // 10 frames per second
  }

  uploadFaces()
}

// 4. UPLOAD DATA
async function uploadFaces() {
  captureStatus.innerText = 'Syncing signatures with server...'

  const form = new FormData()
  form.append('student_id', student_id)
  images.forEach((b, i) => form.append('images[]', b, `face_${i}.jpg`))

  try {
    const resp = await fetch('/upload_face', { method: 'POST', body: form })
    if (resp.ok) {
      captureStatus.innerText = 'Face Capture Complete ✓'
      if (addStudentBtn) addStudentBtn.disabled = false
      alert('Facial data synced successfully!')
    } else {
      throw new Error('Upload failed')
    }
  } catch (err) {
    alert('Upload Error. Please restart capture.')
    captured = 0
    images = []
    startCaptureBtn.disabled = false
  } finally {
    if (stream) stream.getTracks().forEach((t) => t.stop())
  }
}

if (addStudentBtn) {
  addStudentBtn.addEventListener('click', () => {
    window.location.href = '/manage_students' // Redirect to directory instead of home
  })
}
