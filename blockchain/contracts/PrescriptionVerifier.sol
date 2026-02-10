// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title PrescriptionVerifier
 * @dev Smart contract to store and verify prescription PDF hashes
 * Each prescription hash is stored immutably on the blockchain for authenticity verification
 */
contract PrescriptionVerifier {
    
    // Struct to store prescription details
    struct PrescriptionRecord {
        bytes32 pdfHash;         // SHA-256 hash of prescription PDF
        bytes32 doctorHash;      // Hashed doctor ID for privacy
        bytes32 patientHash;     // Hashed patient ID for privacy
        uint256 timestamp;       // Block timestamp when prescription was issued
        uint256 prescriptionId;  // Off-chain prescription ID for reference
        bool exists;             // Flag to check if record exists
        string metadata;         // Optional: Additional metadata (diagnosis, etc.)
    }
    
    // Mapping from PDF hash to prescription record
    mapping(bytes32 => PrescriptionRecord) public prescriptions;
    
    // Mapping to track prescriptions by doctor (hashed)
    mapping(bytes32 => bytes32[]) public doctorPrescriptions;
    
    // Mapping to track prescriptions by patient (hashed)
    mapping(bytes32 => bytes32[]) public patientPrescriptions;
    
    // Counter for total prescriptions
    uint256 public totalPrescriptions;
    
    // Contract owner (hospital/admin)
    address public owner;
    
    // Events
    event PrescriptionStored(
        bytes32 indexed pdfHash,
        bytes32 indexed doctorHash,
        bytes32 indexed patientHash,
        uint256 prescriptionId,
        uint256 timestamp
    );
    
    event PrescriptionVerified(
        bytes32 indexed pdfHash,
        address indexed verifier,
        uint256 timestamp
    );
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        totalPrescriptions = 0;
    }
    
    /**
     * @dev Store a prescription hash on the blockchain
     * @param _pdfHash SHA-256 hash of the prescription PDF
     * @param _doctorHash Hashed doctor identifier
     * @param _patientHash Hashed patient identifier
     * @param _prescriptionId Off-chain prescription ID
     * @param _metadata Optional metadata (JSON string)
     * @return success Whether the operation was successful
     */
    function storePrescription(
        bytes32 _pdfHash,
        bytes32 _doctorHash,
        bytes32 _patientHash,
        uint256 _prescriptionId,
        string memory _metadata
    ) public returns (bool) {
        // Check if prescription hash already exists
        require(!prescriptions[_pdfHash].exists, "Prescription hash already exists");
        
        // Store prescription record
        prescriptions[_pdfHash] = PrescriptionRecord({
            pdfHash: _pdfHash,
            doctorHash: _doctorHash,
            patientHash: _patientHash,
            timestamp: block.timestamp,
            prescriptionId: _prescriptionId,
            exists: true,
            metadata: _metadata
        });
        
        // Track prescriptions by doctor and patient
        doctorPrescriptions[_doctorHash].push(_pdfHash);
        patientPrescriptions[_patientHash].push(_pdfHash);
        
        // Increment counter
        totalPrescriptions++;
        
        // Emit event
        emit PrescriptionStored(
            _pdfHash,
            _doctorHash,
            _patientHash,
            _prescriptionId,
            block.timestamp
        );
        
        return true;
    }
    
    /**
     * @dev Verify if a prescription hash exists on the blockchain
     * @param _pdfHash The prescription PDF hash to verify
     * @return exists Whether the prescription exists
     * @return timestamp When the prescription was issued
     * @return prescriptionId The off-chain prescription ID
     */
    function verifyPrescription(bytes32 _pdfHash) 
        public 
        returns (bool exists, uint256 timestamp, uint256 prescriptionId) 
    {
        PrescriptionRecord memory record = prescriptions[_pdfHash];
        
        // Emit verification event
        if (record.exists) {
            emit PrescriptionVerified(_pdfHash, msg.sender, block.timestamp);
        }
        
        return (record.exists, record.timestamp, record.prescriptionId);
    }
    
    /**
     * @dev Get full prescription details by hash
     * @param _pdfHash The prescription PDF hash
     * @return record The complete prescription record
     */
    function getPrescription(bytes32 _pdfHash) 
        public 
        view 
        returns (PrescriptionRecord memory record) 
    {
        return prescriptions[_pdfHash];
    }
    
    /**
     * @dev Get all prescription hashes for a doctor
     * @param _doctorHash The hashed doctor identifier
     * @return hashes Array of prescription hashes
     */
    function getDoctorPrescriptions(bytes32 _doctorHash) 
        public 
        view 
        returns (bytes32[] memory hashes) 
    {
        return doctorPrescriptions[_doctorHash];
    }
    
    /**
     * @dev Get all prescription hashes for a patient
     * @param _patientHash The hashed patient identifier
     * @return hashes Array of prescription hashes
     */
    function getPatientPrescriptions(bytes32 _patientHash) 
        public 
        view 
        returns (bytes32[] memory hashes) 
    {
        return patientPrescriptions[_patientHash];
    }
    
    /**
     * @dev Transfer contract ownership
     * @param _newOwner New owner address
     */
    function transferOwnership(address _newOwner) public onlyOwner {
        require(_newOwner != address(0), "Invalid new owner address");
        owner = _newOwner;
    }
    
    /**
     * @dev Get contract statistics
     * @return total Total number of prescriptions stored
     * @return contractOwner Contract owner address
     */
    function getStats() 
        public 
        view 
        returns (uint256 total, address contractOwner) 
    {
        return (totalPrescriptions, owner);
    }
}
