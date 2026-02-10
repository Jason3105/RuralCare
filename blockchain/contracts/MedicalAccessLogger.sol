// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title MedicalAccessLogger
 * @dev Smart contract to log and verify medical record access (QR code scans)
 * Each scan is recorded immutably on the blockchain for transparency and auditability
 */
contract MedicalAccessLogger {
    
    // Struct to store access log details
    struct AccessLog {
        bytes32 doctorHash;      // Hashed doctor ID for privacy
        bytes32 patientHash;     // Hashed patient ID for privacy
        uint256 timestamp;       // Block timestamp
        bytes32 accessHash;      // Combined hash for verification
        bool accessGranted;      // Whether access was granted
        string ipfsMetadata;     // Optional: IPFS hash for additional metadata
    }
    
    // Mapping from log ID to AccessLog
    mapping(uint256 => AccessLog) public accessLogs;
    
    // Mapping to track logs by doctor (hashed)
    mapping(bytes32 => uint256[]) public doctorLogs;
    
    // Mapping to track logs by patient (hashed)
    mapping(bytes32 => uint256[]) public patientLogs;
    
    // Counter for log IDs
    uint256 public logCounter;
    
    // Contract owner (hospital/admin)
    address public owner;
    
    // Events
    event AccessLogged(
        uint256 indexed logId,
        bytes32 indexed doctorHash,
        bytes32 indexed patientHash,
        uint256 timestamp,
        bool accessGranted
    );
    
    event AccessVerified(
        uint256 indexed logId,
        address indexed verifier,
        bool isValid
    );
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        logCounter = 0;
    }
    
    /**
     * @dev Log a medical record access event
     * @param _doctorHash Hashed doctor identifier
     * @param _patientHash Hashed patient identifier
     * @param _accessGranted Whether access was granted
     * @param _ipfsMetadata Optional IPFS hash for additional metadata
     * @return logId The ID of the created log
     */
    function logAccess(
        bytes32 _doctorHash,
        bytes32 _patientHash,
        bool _accessGranted,
        string memory _ipfsMetadata
    ) public returns (uint256) {
        logCounter++;
        
        // Create combined hash for verification
        bytes32 accessHash = keccak256(
            abi.encodePacked(_doctorHash, _patientHash, block.timestamp)
        );
        
        // Store access log
        accessLogs[logCounter] = AccessLog({
            doctorHash: _doctorHash,
            patientHash: _patientHash,
            timestamp: block.timestamp,
            accessHash: accessHash,
            accessGranted: _accessGranted,
            ipfsMetadata: _ipfsMetadata
        });
        
        // Track logs by doctor and patient
        doctorLogs[_doctorHash].push(logCounter);
        patientLogs[_patientHash].push(logCounter);
        
        // Emit event
        emit AccessLogged(
            logCounter,
            _doctorHash,
            _patientHash,
            block.timestamp,
            _accessGranted
        );
        
        return logCounter;
    }
    
    /**
     * @dev Verify an access log
     * @param _logId The ID of the log to verify
     * @param _doctorHash Hashed doctor identifier to verify
     * @param _patientHash Hashed patient identifier to verify
     * @return isValid Whether the log is valid
     */
    function verifyAccess(
        uint256 _logId,
        bytes32 _doctorHash,
        bytes32 _patientHash
    ) public returns (bool) {
        require(_logId > 0 && _logId <= logCounter, "Invalid log ID");
        
        AccessLog memory log = accessLogs[_logId];
        
        bool isValid = (
            log.doctorHash == _doctorHash &&
            log.patientHash == _patientHash
        );
        
        emit AccessVerified(_logId, msg.sender, isValid);
        
        return isValid;
    }
    
    /**
     * @dev Get access log details
     * @param _logId The ID of the log
     * @return doctorHash Hashed doctor identifier
     * @return patientHash Hashed patient identifier
     * @return timestamp Block timestamp of access
     * @return accessHash Combined verification hash
     * @return accessGranted Whether access was granted
     * @return ipfsMetadata IPFS metadata string
     */
    function getAccessLog(uint256 _logId) public view returns (
        bytes32 doctorHash,
        bytes32 patientHash,
        uint256 timestamp,
        bytes32 accessHash,
        bool accessGranted,
        string memory ipfsMetadata
    ) {
        require(_logId > 0 && _logId <= logCounter, "Invalid log ID");
        
        AccessLog memory log = accessLogs[_logId];
        
        return (
            log.doctorHash,
            log.patientHash,
            log.timestamp,
            log.accessHash,
            log.accessGranted,
            log.ipfsMetadata
        );
    }
    
    /**
     * @dev Get all log IDs for a doctor
     * @param _doctorHash Hashed doctor identifier
     * @return logIds Array of log IDs
     */
    function getDoctorLogs(bytes32 _doctorHash) public view returns (uint256[] memory logIds) {
        return doctorLogs[_doctorHash];
    }
    
    /**
     * @dev Get all log IDs for a patient
     * @param _patientHash Hashed patient identifier
     * @return logIds Array of log IDs
     */
    function getPatientLogs(bytes32 _patientHash) public view returns (uint256[] memory logIds) {
        return patientLogs[_patientHash];
    }
    
    /**
     * @dev Get total number of logs
     * @return count Total log count
     */
    function getTotalLogs() public view returns (uint256 count) {
        return logCounter;
    }
    
    /**
     * @dev Transfer contract ownership
     * @param newOwner Address of the new owner
     */
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Invalid address");
        owner = newOwner;
    }
}
