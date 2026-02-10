// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ConsultationTokenVerifier
 * @dev Smart contract to store and verify in-person consultation token PDF hashes
 * Each token hash is stored immutably on the blockchain for authenticity verification
 */
contract ConsultationTokenVerifier {
    
    // Struct to store token details
    struct TokenRecord {
        bytes32 pdfHash;         // SHA-256 hash of token PDF
        bytes32 doctorHash;      // Hashed doctor ID for privacy
        bytes32 patientHash;     // Hashed patient ID for privacy
        uint256 timestamp;       // Block timestamp when token was issued
        uint256 tokenNumber;     // Sequential token number per doctor
        bool exists;             // Flag to check if record exists
        string metadata;         // Optional: Additional metadata (consultation info)
    }
    
    // Mapping from PDF hash to token record
    mapping(bytes32 => TokenRecord) public tokens;
    
    // Mapping to track tokens by doctor (hashed)
    mapping(bytes32 => bytes32[]) public doctorTokens;
    
    // Mapping to track tokens by patient (hashed)
    mapping(bytes32 => bytes32[]) public patientTokens;
    
    // Counter for total tokens
    uint256 public totalTokens;
    
    // Contract owner (hospital/admin)
    address public owner;
    
    // Events
    event TokenStored(
        bytes32 indexed pdfHash,
        bytes32 indexed doctorHash,
        bytes32 indexed patientHash,
        uint256 tokenNumber,
        uint256 timestamp
    );
    
    event TokenVerified(
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
        totalTokens = 0;
    }
    
    /**
     * @dev Store a consultation token hash on the blockchain
     * @param _pdfHash SHA-256 hash of the token PDF
     * @param _doctorHash Hashed doctor identifier
     * @param _patientHash Hashed patient identifier
     * @param _tokenNumber Sequential token number for the doctor
     * @param _metadata Optional metadata (JSON string)
     * @return success Whether the operation was successful
     */
    function storeTokenHash(
        bytes32 _pdfHash,
        bytes32 _doctorHash,
        bytes32 _patientHash,
        uint256 _tokenNumber,
        string memory _metadata
    ) public returns (bool) {
        // Check if token hash already exists
        require(!tokens[_pdfHash].exists, "Token hash already exists");
        
        // Store token record
        tokens[_pdfHash] = TokenRecord({
            pdfHash: _pdfHash,
            doctorHash: _doctorHash,
            patientHash: _patientHash,
            timestamp: block.timestamp,
            tokenNumber: _tokenNumber,
            exists: true,
            metadata: _metadata
        });
        
        // Track tokens by doctor and patient
        doctorTokens[_doctorHash].push(_pdfHash);
        patientTokens[_patientHash].push(_pdfHash);
        
        // Increment counter
        totalTokens++;
        
        // Emit event
        emit TokenStored(
            _pdfHash,
            _doctorHash,
            _patientHash,
            _tokenNumber,
            block.timestamp
        );
        
        return true;
    }
    
    /**
     * @dev Verify if a token hash exists on the blockchain
     * @param _pdfHash The token PDF hash to verify
     * @return exists Whether the token exists
     * @return timestamp When the token was issued
     * @return tokenNumber The token number
     */
    function verifyTokenHash(bytes32 _pdfHash) 
        public 
        returns (bool exists, uint256 timestamp, uint256 tokenNumber) 
    {
        TokenRecord memory record = tokens[_pdfHash];
        
        // Emit verification event
        if (record.exists) {
            emit TokenVerified(_pdfHash, msg.sender, block.timestamp);
        }
        
        return (record.exists, record.timestamp, record.tokenNumber);
    }
    
    /**
     * @dev Get full token details by hash
     * @param _pdfHash The token PDF hash
     * @return record The complete token record
     */
    function getTokenRecord(bytes32 _pdfHash) 
        public 
        view 
        returns (TokenRecord memory record) 
    {
        return tokens[_pdfHash];
    }
    
    /**
     * @dev Get all token hashes for a doctor
     * @param _doctorHash The hashed doctor identifier
     * @return hashes Array of token hashes
     */
    function getDoctorTokens(bytes32 _doctorHash) 
        public 
        view 
        returns (bytes32[] memory hashes) 
    {
        return doctorTokens[_doctorHash];
    }
    
    /**
     * @dev Get all token hashes for a patient
     * @param _patientHash The hashed patient identifier
     * @return hashes Array of token hashes
     */
    function getPatientTokens(bytes32 _patientHash) 
        public 
        view 
        returns (bytes32[] memory hashes) 
    {
        return patientTokens[_patientHash];
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
     * @return total Total number of tokens stored
     * @return contractOwner Contract owner address
     */
    function getStats() 
        public 
        view 
        returns (uint256 total, address contractOwner) 
    {
        return (totalTokens, owner);
    }
}
