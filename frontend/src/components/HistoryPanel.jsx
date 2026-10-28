import { useState } from 'react'
import { downloadReport } from '../api'

const CATEGORY_LABEL = {
  no_strong_indicators_found: 'No strong indicators found',
  inconclusive: 'Inconclusive',
  potential_manipulation_indicators: 'Potential inconsistencies',
  analysis_incomplete: 'Analysis incomplete',
}

export default function HistoryPanel({ items, total, loading, error, loaded, onRefresh, onOpen, onDelete, openingId }) {
  const [confirmId, setConfirmId] = useState(null)
  const [rowError, setRowError] = useState('')

  const handleDownload = async (id) => {
    setRowError('')
    try {
      await downloadReport(id)
    } catch (err) {
      setRowError(err.message)
    }
  }

  return (
    <section className="dt-history" id="history" aria-label="Analysis history">
      <div className="dt-dash-head">
        <div>
          <span className="section-kicker">ANALYSIS HISTORY</span>
          <h2>Previous analyses</h2>
          <p className="dt-muted">
            Stored by the backend in its local database{typeof total === 'number' && loaded ? ` · ${total} record${total === 1 ? '' : 's'}` : ''}.
            Original uploads are not saved; a downscaled preview, the ELA map and the PDF are.
          </p>
        </div>
        <button type="button" className="dt-btn" onClick={onRefresh} disabled={loading}>
          {loading ? 'Loading…' : loaded ? 'Refresh' : 'Load history'}
        </button>
      </div>

      {error && (
        <div className="dt-alert dt-alert-red" role="alert">
          {error}
        </div>
      )}
      {rowError && (
        <div className="dt-alert dt-alert-red" role="alert">
          {rowError}
        </div>
      )}

      {loading && !items.length && <p className="dt-muted">Loading analyses…</p>}

      {loaded && !loading && !error && items.length === 0 && (
        <div className="dt-empty">
          <strong>No analyses yet.</strong>
          <p>Analyse an image above and it will appear here.</p>
        </div>
      )}

      {items.length > 0 && (
        <ul className="dt-history-list">
          {items.map((item) => (
            <li key={item.analysis_id} className="dt-history-row">
              <div className="dt-history-main">
                <strong>{item.original_filename || 'Unnamed image'}</strong>
                <span className="dt-muted">
                  {new Date(item.created_at).toLocaleString()} · {item.format || '—'}
                  {item.width && item.height ? ` · ${item.width}×${item.height}` : ''}
                  {item.status === 'partial' ? ' · partial' : ''}
                </span>
                <span className="dt-badge dt-badge-neutral">
                  {CATEGORY_LABEL[item.assessment_category] || 'No assessment'}
                </span>
              </div>
              <div className="dt-history-actions">
                <button type="button" className="dt-btn dt-btn-small" onClick={() => onOpen(item.analysis_id)} disabled={openingId === item.analysis_id}>
                  {openingId === item.analysis_id ? 'Opening…' : 'View'}
                </button>
                {item.report_url && (
                  <button type="button" className="dt-btn dt-btn-small" onClick={() => handleDownload(item.analysis_id)}>
                    PDF
                  </button>
                )}
                {confirmId === item.analysis_id ? (
                  <>
                    <button
                      type="button"
                      className="dt-btn dt-btn-small dt-btn-danger"
                      onClick={async () => {
                        setConfirmId(null)
                        await onDelete(item.analysis_id)
                      }}
                    >
                      Confirm delete
                    </button>
                    <button type="button" className="dt-btn dt-btn-small" onClick={() => setConfirmId(null)}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <button type="button" className="dt-btn dt-btn-small" onClick={() => setConfirmId(item.analysis_id)}>
                    Delete
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
