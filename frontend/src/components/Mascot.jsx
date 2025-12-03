import React from 'react';
import './mascot.css';

export default function Mascot({ focusedField, isTypingPassword }) {
  let stateClass = 'mascot--idle';
  if (focusedField === 'email') stateClass = 'mascot--look';
  if (focusedField === 'password' && isTypingPassword) stateClass = 'mascot--cover';

  return (
    <div className={`mascot ${stateClass}`}>
      <div className="mascot-head">
        <div className="mascot-eye mascot-eye-left" />
        <div className="mascot-eye mascot-eye-right" />
        <div className="mascot-hand mascot-hand-left" />
        <div className="mascot-hand mascot-hand-right" />
      </div>
    </div>
  );
}
