/* Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later */
const form = document.querySelector('#login-form');
form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button');
  const error = document.querySelector('#login-error');
  button.disabled = true;
  error.textContent = '';
  try {
    const response = await fetch('/api/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(Object.fromEntries(new FormData(form)))});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Confira os campos informados.');
    location.replace('/');
  } catch (failure) {
    error.textContent = failure.message;
  } finally {
    button.disabled = false;
  }
});
