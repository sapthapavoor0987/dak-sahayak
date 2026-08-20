'use client';

import { useState } from 'react';
import { fillFormPdf } from '../lib/api';

export default function FormDownloadCard({ scheme = 'ppf', language = 'en', data = {} }) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState('');

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError('');
    try {
      await fillFormPdf({ scheme, language, data });
    } catch (err) {
      console.error('Download error:', err);
      setDownloadError(err.message || 'Failed to generate PDF');
    } finally {
      setDownloading(false);
    }
  };

  const applicantName = data.applicant_name || 'Applicant';
  const pan = data.pan || 'N/A';
  const deposit = data.initial_deposit ? `₹${Number(data.initial_deposit).toLocaleString('en-IN')}` : '₹500';
  const nominee = data.nominee_name || 'N/A';

  return (
    <div style={{
      marginTop: '14px',
      backgroundColor: 'var(--card-bg, #1a1a24)',
      border: '1px solid rgba(245, 166, 35, 0.35)',
      borderRadius: '12px',
      padding: '18px',
      maxWidth: '560px',
      boxShadow: '0 8px 24px rgba(0,0,0,0.35)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem', color: 'var(--accent-red, #e53935)' }}>
            <i className="fa-solid fa-file-pdf"></i>
          </span>
          <div>
            <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-bright, #fff)' }}>
              Official India Post Form-1 (GSPR 2018)
            </h4>
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-gold, #f5a623)', fontWeight: 500 }}>
              {scheme.toUpperCase()} Account Opening Form
            </span>
          </div>
        </div>
        <span style={{
          fontSize: '0.7rem',
          backgroundColor: 'rgba(39, 174, 96, 0.2)',
          color: '#2ecc71',
          padding: '3px 8px',
          borderRadius: '12px',
          fontWeight: 600,
          border: '1px solid rgba(46, 204, 113, 0.3)'
        }}>
          ✓ Ready to Print
        </span>
      </div>

      {/* Summary Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '8px',
        fontSize: '0.8rem',
        backgroundColor: 'rgba(255,255,255,0.03)',
        padding: '10px 12px',
        borderRadius: '8px',
        marginBottom: '14px'
      }}>
        <div>
          <span style={{ color: 'var(--text-muted, #888)' }}>Applicant:</span>{' '}
          <strong style={{ color: 'var(--text-bright, #fff)' }}>{applicantName}</strong>
        </div>
        <div>
          <span style={{ color: 'var(--text-muted, #888)' }}>PAN:</span>{' '}
          <strong style={{ color: 'var(--text-bright, #fff)' }}>{pan}</strong>
        </div>
        <div>
          <span style={{ color: 'var(--text-muted, #888)' }}>Initial Deposit:</span>{' '}
          <strong style={{ color: 'var(--accent-gold, #f5a623)' }}>{deposit}</strong>
        </div>
        <div>
          <span style={{ color: 'var(--text-muted, #888)' }}>Nominee:</span>{' '}
          <strong style={{ color: 'var(--text-bright, #fff)' }}>{nominee}</strong>
        </div>
      </div>

      {/* Primary Download Action */}
      <button
        onClick={handleDownload}
        disabled={downloading}
        style={{
          width: '100%',
          backgroundColor: 'var(--accent-red, #d32f2f)',
          color: '#fff',
          border: 'none',
          padding: '11px 16px',
          borderRadius: '8px',
          fontWeight: 600,
          fontSize: '0.9rem',
          cursor: downloading ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          transition: 'all 0.2s ease',
          boxShadow: '0 4px 12px rgba(211, 47, 47, 0.3)'
        }}
      >
        {downloading ? (
          <>
            <i className="fa-solid fa-spinner fa-spin"></i>
            <span>Generating Print-Ready PDF...</span>
          </>
        ) : (
          <>
            <i className="fa-solid fa-download"></i>
            <span>Download Filled Form-1 PDF</span>
          </>
        )}
      </button>

      {downloadError && (
        <p style={{ color: '#ff6b6b', fontSize: '0.75rem', marginTop: '8px', textAlign: 'center' }}>
          ⚠️ {downloadError}
        </p>
      )}

      {/* Important Government Counter Disclaimers */}
      <div style={{
        marginTop: '12px',
        padding: '10px',
        backgroundColor: 'rgba(245, 166, 35, 0.08)',
        borderLeft: '3px solid var(--accent-gold, #f5a623)',
        borderRadius: '4px',
        fontSize: '0.74rem',
        lineHeight: '1.4',
        color: 'var(--text-muted, #ccc)'
      }}>
        <strong style={{ color: 'var(--accent-gold, #f5a623)', display: 'block', marginBottom: '4px' }}>
          <i className="fa-solid fa-circle-info"></i> Pre-Fill Aid — Next Steps for Submission:
        </strong>
        <ol style={{ margin: '4px 0 0 16px', padding: 0 }}>
          <li>Print this 2-page form on A4 paper.</li>
          <li>Affix your recent passport-size photograph in the designated box on Page 1.</li>
          <li><strong>Sign the declaration</strong> and specimen signature boxes (Pages 1 & 2).</li>
          <li>Attach self-attested photocopies of your <strong>Aadhaar Card</strong> & <strong>PAN Card</strong>.</li>
          <li>Submit along with your deposit (Cash/Cheque) at your nearest Post Office counter.</li>
        </ol>
      </div>
    </div>
  );
}
