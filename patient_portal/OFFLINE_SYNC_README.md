# Offline Sync Feature for Patient Portal

## Overview

The Offline Sync feature allows patients to use the patient portal even when they have low or no internet connectivity. Operations performed offline are automatically queued and synchronized when the connection is restored.

## Features

- **Offline Symptom Logging**: Patients can log their symptoms even without internet connection
- **Offline Alert Management**: Mark alerts as read while offline
- **Automatic Sync**: Automatically syncs queued operations when connection is restored
- **Offline Data Cache**: Caches essential patient data for offline viewing
- **Connection Status Indicator**: Visual indicator showing online/offline status
- **Service Worker**: Caches essential resources for offline access

## Architecture

### Backend Components

1. **Models** (`patient_portal/models.py`):
   - `OfflineSyncQueue`: Tracks operations that need to be synced
   - `OfflineDataCache`: Stores cached patient data for offline access

2. **Views** (`patient_portal/offline_sync_views.py`):
   - `sync_status`: Get sync status and pending operations count
   - `sync_operations`: Batch sync pending operations
   - `get_offline_cache`: Get cached data for offline access

3. **URLs** (`patient_portal/urls.py`):
   - `/portal/api/offline/sync-status/`: Get sync status
   - `/portal/api/offline/sync/`: Sync operations
   - `/portal/api/offline/cache/`: Get offline cache

### Frontend Components

1. **IndexedDB Utilities** (`static/patient_portal/offline-db.js`):
   - Manages local IndexedDB database
   - Stores sync queue, offline cache, symptom logs, and alerts

2. **Offline Sync Manager** (`static/patient_portal/offline-sync.js`):
   - Handles online/offline detection
   - Manages sync queue
   - Automatically syncs when connection is restored

3. **Offline Form Handler** (`static/patient_portal/offline-forms.js`):
   - Intercepts form submissions
   - Queues operations when offline
   - Handles offline symptom logging and alert management

4. **Service Worker** (`static/patient_portal/service-worker.js`):
   - Caches essential resources
   - Enables offline page access

## Setup

### 1. Run Database Migration

```bash
python manage.py migrate patient_portal
```

### 2. Collect Static Files

```bash
python manage.py collectstatic
```

### 3. Service Worker Registration

The service worker is automatically registered when a patient user loads the portal. The registration happens in `templates/base.html`.

## Usage

### For Patients

1. **Offline Symptom Logging**:
   - Fill out the symptom log form as usual
   - If offline, the form will be saved locally and queued for sync
   - A notification will appear confirming the offline save
   - When connection is restored, the log will be automatically synced

2. **Offline Alert Management**:
   - Click "Mark as read" on any alert
   - If offline, the action will be queued
   - When connection is restored, the action will be synced

3. **Connection Status**:
   - A status indicator appears in the bottom-right corner
   - Green = Online, Red = Offline
   - The indicator automatically updates based on connection status

### For Developers

#### Adding New Offline Operations

1. **Add to Sync Queue**:
   ```javascript
   await offlineSyncManager.queueOperation('operation_type', {
       // operation data
   });
   ```

2. **Handle in Backend**:
   - Add operation type to `OfflineSyncQueue.OPERATION_TYPE_CHOICES`
   - Add handler function in `offline_sync_views.py`:
     ```python
     def _sync_your_operation(patient, data):
         # Handle the operation
         return {'success': True, 'server_id': str(obj.id)}
     ```
   - Add case in `sync_operations` view

#### Supported Operation Types

- `symptom_log`: Create a symptom log
- `alert_read`: Mark an alert as read
- `alert_read_all`: Mark all alerts as read
- `notification_preference`: Update notification preferences

## Technical Details

### IndexedDB Schema

- **syncQueue**: Stores pending sync operations
- **offlineCache**: Stores cached patient data
- **symptomLogs**: Stores symptom logs for offline viewing
- **alerts**: Stores alerts for offline viewing

### Sync Process

1. When offline, operations are stored in IndexedDB
2. When connection is restored, operations are batched and sent to server
3. Server processes operations and returns results
4. Successfully synced operations are removed from queue
5. Failed operations are retried (max 5 retries)
6. Conflicts are handled (e.g., duplicate symptom log for same date)

### Conflict Resolution

- **Symptom Log Conflicts**: If a log already exists for the same date, the server returns a conflict error
- **Other Conflicts**: Server-side validation handles conflicts based on operation type

## Browser Compatibility

- **Chrome/Edge**: Full support (IndexedDB, Service Worker)
- **Firefox**: Full support
- **Safari**: Full support (iOS 11.3+)
- **Opera**: Full support

## Limitations

1. **Read-Only Operations**: Currently only write operations (create, update) are supported offline
2. **File Uploads**: File uploads are not supported offline
3. **Real-time Features**: Video calls and real-time features require internet connection
4. **Cache Size**: IndexedDB has storage limits (typically 50% of disk space)

## Troubleshooting

### Service Worker Not Registering

- Check browser console for errors
- Ensure HTTPS is used (or localhost for development)
- Check browser permissions for service workers

### Sync Not Working

- Check browser console for errors
- Verify API endpoints are accessible
- Check network tab for failed requests
- Verify CSRF token is being sent

### Data Not Persisting

- Check IndexedDB in browser DevTools
- Verify browser storage permissions
- Check for storage quota exceeded errors

## Future Enhancements

- [ ] Support for offline consultation requests
- [ ] Offline prescription viewing
- [ ] Background sync API integration
- [ ] Conflict resolution UI
- [ ] Sync progress indicator
- [ ] Manual sync trigger
- [ ] Offline data export

## Support

For issues or questions, please contact the development team or create an issue in the project repository.
