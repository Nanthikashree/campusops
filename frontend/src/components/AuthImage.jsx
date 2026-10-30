import { useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";

export default function AuthImage({ id, alt, onOpen }) {
  const { callBlob } = useAuth();
  const [src, setSrc] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let url = null;
    let alive = true;
    callBlob(`/api/attachments/${id}/file`)
      .then((b) => {
        if (!alive) return;
        url = URL.createObjectURL(b);
        setSrc(url);
      })
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [id]);

  if (failed) return <div className="small">Image unavailable</div>;
  if (!src) return <div className="thumb skeleton" />;
  return <img className="thumb" src={src} alt={alt} onClick={() => onOpen && onOpen(src)} />;
}