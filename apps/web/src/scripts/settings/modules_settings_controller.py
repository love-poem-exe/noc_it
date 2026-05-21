#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

# Dodaj podstawowe nagłówki CORS ręcznie
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '../../data/modules_settings.json')

def load_settings():
    """Wczytuje ustawienia modułów z pliku JSON"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Domyślne ustawienia
            default_settings = {
                "cmtsTmpfs": {
                    "hoursBack": 24,
                    "restartLookback": 12
                },
                "cmtsSwapper": {
                    "enabled": True
                },
                "console": {
                    "maxLines": 1000,
                    "autoScroll": True
                }
            }
            save_settings(default_settings)
            return default_settings
    except Exception as e:
        print(f"[MODULES SETTINGS] Error loading settings: {e}")
        return {}

def save_settings(settings):
    """Zapisuje ustawienia modułów do pliku JSON"""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[MODULES SETTINGS] Error saving settings: {e}")
        return False

@app.route('/api/modules/settings', methods=['GET'])
def get_settings():
    """Endpoint do pobierania ustawień modułów"""
    try:
        settings = load_settings()
        return jsonify({
            'success': True,
            'data': settings
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/modules/settings', methods=['POST'])
def update_settings():
    """Endpoint do aktualizacji ustawień modułów"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Wczytaj obecne ustawienia
        current_settings = load_settings()
        
        # Aktualizuj z nowymi danymi
        current_settings.update(data)
        
        # Zapisz zaktualizowane ustawienia
        if save_settings(current_settings):
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully',
                'data': current_settings
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save settings'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/modules/settings/<module_name>', methods=['GET'])
def get_module_settings(module_name):
    """Endpoint do pobierania ustawień konkretnego modułu"""
    try:
        settings = load_settings()
        module_settings = settings.get(module_name, {})
        
        return jsonify({
            'success': True,
            'module': module_name,
            'data': module_settings
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/modules/settings/<module_name>', methods=['PUT'])
def update_module_settings(module_name):
    """Endpoint do aktualizacji ustawień konkretnego modułu"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Wczytaj obecne ustawienia
        current_settings = load_settings()
        
        # Aktualizuj ustawienia modułu
        current_settings[module_name] = data
        
        # Zapisz zaktualizowane ustawienia
        if save_settings(current_settings):
            return jsonify({
                'success': True,
                'message': f'Settings for {module_name} updated successfully',
                'data': current_settings[module_name]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save settings'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("[MODULES SETTINGS] Starting modules settings server...")
    print(f"[MODULES SETTINGS] Settings file: {SETTINGS_FILE}")
    app.run(host='0.0.0.0', port=5006, debug=True)