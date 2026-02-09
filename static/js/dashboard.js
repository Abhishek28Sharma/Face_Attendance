document.addEventListener('DOMContentLoaded', () => {
  const trainBtn = document.getElementById('trainBtn')
  const trainProgress = document.getElementById('trainProgress')
  const trainProgressVal = document.getElementById('trainProgressVal')
  const trainMsg = document.getElementById('trainMsg')

  // 1. Helper to update the Progress Bar UI
  async function pollStatus() {
    try {
      const res = await fetch('/train_status')
      const data = await res.json()

      if (trainProgress) trainProgress.style.width = data.progress + '%'
      if (trainProgressVal) trainProgressVal.innerText = data.progress

      // Keep the most recent message visible
      if (trainMsg && data.message) trainMsg.innerText = data.message

      return data
    } catch (e) {
      console.error('Status Poll Error:', e)
      return null
    }
  }

  // 2. GLOBAL TRAINING LOGIC
  trainBtn.addEventListener('click', async () => {
    // UI Feedback and state locking
    trainBtn.disabled = true
    trainBtn.innerText = 'Syncing...'
    if (trainMsg) trainMsg.innerText = 'Initializing Neural Engine...'

    try {
      // Start the training thread
      const start = await fetch('/train_model', { method: 'POST' })

      if (!start.ok && start.status !== 202) {
        alert('Failed to start training engine.')
        trainBtn.disabled = false
        trainBtn.innerText = 'Sync AI Model'
        return
      }

      // Start Polling every 1.5 seconds
      const pollInterval = setInterval(async () => {
        const status = await pollStatus()

        // Stop when backend marks 'running' as false
        if (status && status.running === false) {
          clearInterval(pollInterval)
          trainBtn.disabled = false
          trainBtn.innerText = 'Sync AI Model'

          // Final confirmation logic
          if (status.progress >= 100) {
            trainMsg.innerHTML =
              '<span class="text-emerald-500 font-bold">Neural signatures synchronized! model.pkl is ready.</span>'
          } else {
            // This helps identify if training failed due to lack of students
            trainMsg.innerHTML = `<span class="text-red-400 font-bold">${status.message || 'Sync failed.'}</span>`
          }
        }
      }, 1500)
    } catch (error) {
      console.error('Training Error:', error)
      alert('Network error: Could not reach the server.')
      trainBtn.disabled = false
      trainBtn.innerText = 'Sync AI Model'
    }
  })

  // 3. ATTENDANCE CHART LOGIC
  let chart = null
  async function updateChart() {
    try {
      const res = await fetch('/attendance_stats')
      if (!res.ok) return
      const data = await res.json()
      const chartCanvas = document.getElementById('attendanceChart')
      if (!chartCanvas) return

      const ctx = chartCanvas.getContext('2d')
      if (!chart) {
        chart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: data.dates,
            datasets: [
              {
                label: 'Attendance Count',
                data: data.counts,
                backgroundColor: 'rgba(59,130,246,0.7)',
                borderRadius: 8,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                grid: { color: 'rgba(255,255,255,0.05)' },
              },
              x: { grid: { display: false } },
            },
          },
        })
      } else {
        chart.data.labels = data.dates
        chart.data.datasets[0].data = data.counts
        chart.update()
      }
    } catch (e) {
      console.error('Chart update failed:', e)
    }
  }

  updateChart()
  setInterval(updateChart, 15000)
})
