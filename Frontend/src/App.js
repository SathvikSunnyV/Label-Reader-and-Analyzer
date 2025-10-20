import React, { useState, useRef, useCallback } from 'react';
import styled, { keyframes, css } from 'styled-components';
import ReactCrop, { centerCrop, makeAspectCrop } from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css'; 
import Tesseract from 'tesseract.js';
const Theme = {
    primary: '#4c0082',
    primaryLight: '#2c3e50',
    accent: '#FFD700',
    secondary: '#e0e0e0',
    success: '#17c964', 
    warning: '#FFC107', 
    danger: '#dc3545', 
    backgroundStart: '#050c18', 
    backgroundEnd: '#1a335a', 
    cardBg: 'rgba(255, 255, 255, 0.98)', 
    textDark: '#1a1a2e', 
    textLight: '#f4f4f4',
};

const pulse = keyframes`
  0% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.03); opacity: 1; } 
  100% { transform: scale(1); opacity: 0.8; }
`;

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center; 
  min-height: 100vh; 
  padding: 30px 5px; 
  box-sizing: border-box;
  background: linear-gradient(135deg, ${Theme.backgroundStart} 0%, ${Theme.backgroundEnd} 100%);
  color: ${Theme.textDark}; 
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
`;

const Header = styled.header`
  width: 100%;
  max-width: 800px; 
  padding: 10px 0; 
  margin-bottom: 35px; 
  text-align: center;
  flex-shrink: 0;
`;

const Title = styled.h1`
  color: ${Theme.textLight}; 
  font-size: 2.6em; 
  margin: 0;
  font-weight: 900; 
  letter-spacing: 1.5px; 
  text-shadow: 0 4px 8px rgba(0,0,0,0.7); 
`;

const MainContent = styled.div`
  display: flex; 
  flex-direction: column; 
  align-items: center; 
  gap: 30px; 
  width: 100%;
  max-width: 650px; 
  background-color: transparent; 
  padding: 0; 
  flex-grow: 1; 
  min-height: 0;
`;

const SectionContainer = styled.div`
  padding: 35px; 
  border-radius: 20px; 
  background-color: ${Theme.cardBg}; 
  box-shadow: 
    0 20px 50px rgba(0, 0, 0, 0.35), 
    inset 0 0 0 1px rgba(255, 255, 255, 0.1); 
  backdrop-filter: blur(8px); 
  -webkit-backdrop-filter: blur(8px);
  display: flex; 
  flex-direction: column;
  align-items: center; 
  width: 100%; 
  box-sizing: border-box;
  transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  
  &:hover {
      transform: translateY(-10px); 
      box-shadow: 
        0 25px 60px rgba(0, 0, 0, 0.45),
        inset 0 0 0 1px rgba(255, 255, 255, 0.2);
  }
`;

const SectionTitle = styled.h2`
  color: ${Theme.textDark};
  border-bottom: 1px solid ${Theme.secondary}; 
  padding-bottom: 12px; 
  margin-top: 0;
  margin-bottom: 30px; 
  font-size: 1.7em; 
  font-weight: 800;
  flex-shrink: 0;
  width: 100%; 
  text-align: center;
`;

const ButtonBase = css`
    padding: 14px 28px; 
    color: ${Theme.textLight};
    border: none;
    border-radius: 10px; 
    cursor: pointer;
    font-size: 1.1em; 
    font-weight: 700;
    transition: all 0.3s ease-in-out;
    width: 90%; 
    max-width: 380px; 
    margin-top: 30px; 
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); 
    flex-shrink: 0;
    position: relative;
    overflow: hidden;

    &::before {
        content: '';
        position: absolute;
        top: 0;
        left: -150%;
        width: 100%;
        height: 100%;
        background: rgba(255, 215, 0, 0.3); 
        transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
        transform: skewX(-30deg);
    }

    &:hover::before {
        left: 150%;
    }

    &:hover:not(:disabled) {
        transform: translateY(-5px); 
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.55);
    }

    &:active {
        transform: translateY(-1px);
        box-shadow: 0 5px 10px rgba(0, 0, 0, 0.3);
    }
    
    &:disabled {
        background-color: ${Theme.secondary};
        cursor: not-allowed;
        transform: none;
        box-shadow: none;
    }
`;

const PrimaryButton = styled.button`
    ${ButtonBase}
    background: linear-gradient(90deg, ${Theme.primary} 0%, #7e3e9d 100%); 
    
    &:hover:not(:disabled) {
        background: linear-gradient(90deg, #380060 0%, ${Theme.primary} 100%);
    }
`;

const SuccessButton = styled.button`
    ${ButtonBase}
    background: linear-gradient(90deg, ${Theme.success} 0%, #17a950 100%); 

    &:hover:not(:disabled) {
        background: linear-gradient(90deg, #107c39 0%, ${Theme.success} 100%);
    }
`;

const HiddenFileInput = styled.input`
  display: none; 
`;

const UploadButton = styled(PrimaryButton)`
  margin-top: 0; 
  margin-bottom: 15px;
`;

const CropContainer = styled.div`
    width: 100%;
    flex-grow: 1; 
    margin-bottom: 25px; 
    border: 3px solid ${Theme.secondary}; 
    padding: 10px; 
    border-radius: 12px;
    background-color: #ffffff; 
    min-height: 250px; 
    max-height: 650px; 
    overflow: hidden; 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    box-shadow: inset 0 0 15px rgba(0,0,0,0.2); 
    
    .ReactCrop {
        max-width: 100%;
        max-height: 600px; 
        height: 100%; 
        width: auto; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        margin: 0; 
        cursor: crosshair;

        .ReactCrop--fixed-aspect {
            border-color: ${Theme.accent} !important;
        }
    }
`;

const StatusText = styled.p`
    color: ${Theme.textDark};
    font-weight: 700; 
    font-size: 1.1em; 
    margin-top: 15px; 
    margin-bottom: 15px; 
    flex-shrink: 0;
    width: 100%; 
    text-align: center;
    
    ${({ isLoading }) => isLoading && css`
        color: ${Theme.primary}; 
        animation: ${pulse} 1.5s infinite ease-in-out;
    `}

    ${({ isGuidance }) => isGuidance && css`
        color: ${Theme.textDark}; 
        font-weight: 600;
        font-style: italic;
        margin-top: 0;
        margin-bottom: 15px; 
        padding: 5px 0;
        border-bottom: 1px dashed ${Theme.secondary};
        width: 85%;
        max-width: 380px;
    `}
`;

const StyledTextArea = styled.textarea`
    width: 100%;
    padding: 18px; 
    border: 2px solid ${Theme.secondary}; 
    border-radius: 10px; 
    box-sizing: border-box;
    font-family: 'Roboto Mono', monospace; 
    font-size: 1em; 
    flex-grow: 1; 
    min-height: 250px; 
    margin-top: 25px; 
    margin-bottom: 25px; 
    transition: border-color 0.3s, box-shadow 0.3s;
    resize: vertical; 
    color: ${Theme.textDark};
    box-shadow: inset 0 2px 6px rgba(0,0,0,0.1); 

    &:focus {
        border-color: ${Theme.accent}; 
        box-shadow: 0 0 0 4px rgba(255, 215, 0, 0.3); 
        outline: none;
    }
`;

function canvasPreview(image, crop) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) throw new Error('No 2d context');
    
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;
    
    const pixelCrop = {
        x: crop.x * scaleX,
        y: crop.y * scaleY,
        width: crop.width * scaleX,
        height: crop.height * scaleY,
    };

    canvas.width = pixelCrop.width;
    canvas.height = pixelCrop.height;

    ctx.drawImage(
        image, pixelCrop.x, pixelCrop.y, pixelCrop.width, pixelCrop.height, 0, 0, pixelCrop.width, pixelCrop.height, 
    );
    return canvas;
}

function parseIngredientsFromText(text) {
  if (!text) return [];
  const rawParts = text
    .split(/[\n•\u2022,;\/]+/)
    .map(s => s.trim())
    .filter(Boolean);

  const final = [];
  rawParts.forEach(part => {
    const subParts = part.split(/\s+(?:and|&)\s+/i).map(s => s.trim()).filter(Boolean);
    subParts.forEach(sp => {
      const cleaned = sp.replace(/^\(+|\)+$/g, '').replace(/\b\d+(\.\d+)?\s*(mg|g|kg|ml|%)\b/gi, '').trim();
      if (cleaned) final.push(cleaned);
    });
  });

  return Array.from(new Set(final));
}

function App() {
  const [imgSrc, setImgSrc] = useState('');
  const [crop, setCrop] = useState();
  const imgRef = useRef(null);
  const [completedCrop, setCompletedCrop] = useState(null);
  const fileInputRef = useRef(null); 
  
  const initialOcrText = 'Extracted text will appear here. Edit as needed before submitting.';
  const [ocrResult, setOcrResult] = useState(initialOcrText);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [showOcrResult, setShowOcrResult] = useState(false); 

  const [backendLoading, setBackendLoading] = useState(false);
  const [backendError, setBackendError] = useState('');

  const onSelectFile = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setCrop(undefined); 
      setCompletedCrop(null);
      setOcrResult(initialOcrText); 
      setShowOcrResult(false); 
      setBackendResults([]);
      setBackendError('');

      const reader = new FileReader();
      reader.addEventListener('load', () =>
        setImgSrc(reader.result?.toString() || ''),
      );
      reader.readAsDataURL(e.target.files[0]);
    }
  };

  const onImageLoad = useCallback((e) => {
    imgRef.current = e.currentTarget;
    const { width, height } = e.currentTarget;
    
    setCrop(centerCrop(
        makeAspectCrop(
            { unit: '%', width: 90, height: 90 },
            undefined,
            width,
            height,
        ),
        width,
        height,
    ));
    
  }, []);

  const handleCropProcess = () => {
    if (!completedCrop || !imgRef.current) return;
    
    setOcrLoading(true);
    setOcrResult('Extracting text...');
    setShowOcrResult(true); 

    const image = imgRef.current;
    const crop = completedCrop;
    const canvas = canvasPreview(image, crop);

    canvas.toBlob((blob) => {
        if (blob) {
            Tesseract.recognize(
                blob, 
                'eng', 
                { logger: m => {  } }
            ).then(({ data: { text } }) => {
                setOcrResult(text.trim() || 'No text found.');
                setOcrLoading(false);
            }).catch(error => {
                console.error('Tesseract OCR Error:', error);
                setOcrResult('Error during OCR extraction.');
                setOcrLoading(false);
            });
        }
    }, 'image/jpeg');
  };
  
  const handleSubmission = async () => {
      if (!ocrResult || ocrResult.trim() === initialOcrText) {
          alert("Please extract and edit the ingredients before proceeding.");
          return;
      }

      const parsedIngredients = parseIngredientsFromText(ocrResult);
      if (parsedIngredients.length === 0) {
        alert('No ingredients detected. Please edit the extracted text to include ingredient names separated by commas or new lines.');
        return;
      }

      const payload = { ingredients: parsedIngredients };

      setBackendResults([]);
      setBackendError('');
      setBackendLoading(true);

      try {
        const res = await fetch('http://localhost:5000/process_ingredients', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const text = await res.text().catch(() => '');
          throw new Error(`Backend error: ${res.status} ${res.statusText} ${text}`);
        }

        const json = await res.json();
        setBackendResults(Array.isArray(json.results) ? json.results : []);
      } catch (err) {
        console.error('Submission error:', err);
        setBackendError(err.message || 'Unknown error while contacting backend.');
      } finally {
        setBackendLoading(false);
        alert('Proceeding Complete! Data sent for details/verification.');
      }
  };

  return (
    <PageContainer>
      <Header>
        <Title>INGREDIENTS VERIFICATION</Title>
      </Header>
      
      <MainContent>
        <SectionContainer>
          <SectionTitle>Upload an Image</SectionTitle>
          
          <HiddenFileInput 
              type="file" 
              accept="image/*" 
              onChange={onSelectFile}
              ref={fileInputRef}
          />
          
          <UploadButton onClick={() => fileInputRef.current.click()}>
              {imgSrc ? 'Change Image' : 'Upload Image'}
          </UploadButton>

          {imgSrc && (
            <>
                <CropContainer>
                    <ReactCrop 
                        crop={crop} 
                        onChange={c => setCrop(c)} 
                        onComplete={(c) => setCompletedCrop(c)}
                        aspect={undefined} 
                    >
                        <img 
                            ref={imgRef} 
                            alt="Upload source" 
                            src={imgSrc} 
                            onLoad={onImageLoad}
                        />
                    </ReactCrop>
                </CropContainer>

                <StatusText isGuidance>
                    Crop the image to the ingredients
                </StatusText>

                <PrimaryButton 
                    onClick={handleCropProcess}
                    disabled={!completedCrop || !completedCrop.width || !completedCrop.height || ocrLoading}
                >
                    {ocrLoading ? 'Processing...' : 'Extract Text'}
                </PrimaryButton>
            </>
          )}

          {showOcrResult && (
              <>
                  <StatusText isLoading={ocrLoading}>
                    Status: {ocrLoading ? 'Extracting Text...' : 'Ready for Verification'}
                  </StatusText>
                  
                  <StyledTextArea
                      value={ocrResult}
                      onChange={(e) => setOcrResult(e.target.value)}
                  />
                  
                  <StatusText isGuidance>
                      Edit the extracted text if there are any mistakes
                  </StatusText>

                  <SuccessButton 
                      onClick={handleSubmission}
                      disabled={backendLoading || ocrLoading}
                  >
                      {backendLoading ? 'Sending...' : 'Proceed for Details'}
                  </SuccessButton>

                  {}
                  {backendError && (
                    <StatusText style={{ color: Theme.danger }}>
                      Error: {backendError}
                    </StatusText>
                  )}

                  {backendResults.length > 0 && (
                    <div style={{ width: '100%', marginTop: '18px' }}>
                      <SectionTitle style={{ fontSize: '1.2em' }}>Analyzed Results</SectionTitle>
                      {backendResults.map((item, idx) => (
                        <div key={idx} style={{ border: '1px solid #eee', padding: '12px', margin: '10px 0', borderRadius: '8px' }}>
                          <strong>{item.ingredient}</strong>
                          <p style={{ margin: '6px 0' }}><strong>Usage:</strong> {item.usage || 'N/A'}</p>
                          <p style={{ margin: '6px 0' }}><strong>Health Verdict:</strong> {item.health?.verdict || 'Unknown'}</p>
                          {item.health?.reason && <p style={{ margin: '6px 0' }}><strong>Reason:</strong> {item.health.reason}</p>}
                          <p style={{ margin: '6px 0' }}><strong>Banned in:</strong> {(item.banned_countries && item.banned_countries.length>0) ? item.banned_countries.join(', ') : 'None'}</p>
                        </div>
                      ))}
                    </div>
                  )}
              </>
          )}

        </SectionContainer>
      </MainContent>
    </PageContainer>
  );
}

export default App;
