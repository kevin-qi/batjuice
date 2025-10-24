/*
 * BatFeeder Arduino Controller
 *
 * Hardware:
 * - Arduino Uno
 * - Adafruit Motor Shield V3
 * - Motors on M1, M2, M3, M4 (feeders 0-3, up to 4 total)
 * - Beam break sensors on digital pins
 * - TTL input/output
 *
 * Communication Protocol:
 * Receives: MOTOR:feeder_id:duration_ms:speed
 * Sends: BEAM:feeder_id, TTL, ERROR:message
 *
 * Supports 1-4 feeders dynamically - works regardless of how many are physically connected
 */

 #include <Adafruit_MotorShield.h>

 // Motor Shield Setup
 Adafruit_MotorShield AFMS = Adafruit_MotorShield();
 Adafruit_DCMotor *motor1 = AFMS.getMotor(1);  // M1 - Feeder 0
 Adafruit_DCMotor *motor2 = AFMS.getMotor(2);  // M2 - Feeder 1
 Adafruit_DCMotor *motor3 = AFMS.getMotor(3);  // M3 - Feeder 2
 Adafruit_DCMotor *motor4 = AFMS.getMotor(4);  // M4 - Feeder 3

 // Pin Definitions
 const int BEAM_BREAK_PIN_0 = 2;    // Beam break sensor for feeder 0
 const int BEAM_BREAK_PIN_1 = 3;    // Beam break sensor for feeder 1
 const int BEAM_BREAK_PIN_2 = 4;    // Beam break sensor for feeder 2
 const int BEAM_BREAK_PIN_3 = 5;    // Beam break sensor for feeder 3
 const int TTL_INPUT_PIN = 6;       // TTL input pin
 const int TTL_OUTPUT_PIN = 7;      // TTL output pin
 const int LED_PIN = 13;            // Built-in LED for status

 // Motor Control Variables
struct MotorState {
  bool running;
  unsigned long start_time;
  unsigned long duration;
  Adafruit_DCMotor* motor;
  bool stop_requested;  // Flag for interrupt-based stopping
  unsigned long actual_stop_time;  // When interrupt actually triggered
  int speed;  // Motor speed (0-255)
};

 MotorState motors[4];  // For feeders 0-3 (up to 4 feeders)

// Timer interrupt variables
volatile bool timer_interrupt_flag = false;
volatile unsigned long interrupt_counter = 0;
volatile unsigned long motor_target_times[4] = {0, 0, 0, 0};  // Target stop times for each motor

 // Beam Break Detection
const int BEAM_BREAK_PINS[4] = {BEAM_BREAK_PIN_0, BEAM_BREAK_PIN_1, BEAM_BREAK_PIN_2, BEAM_BREAK_PIN_3};
bool beam_break_state[4] = {HIGH, HIGH, HIGH, HIGH};  // Previous states (HIGH = no break)
unsigned long last_beam_check = 0;
const unsigned long BEAM_CHECK_INTERVAL = 5;  // Check every 5ms (faster for responsiveness)

// TTL Handling
bool ttl_input_state = LOW;
unsigned long last_ttl_check = 0;
const unsigned long TTL_CHECK_INTERVAL = 2;  // Check every 2ms (faster for responsiveness)

 // Serial Communication
 String input_buffer = "";
 const unsigned long SERIAL_TIMEOUT = 100;

 void setup() {
   // Initialize Serial
   Serial.begin(9600);
   Serial.println("BatFeeder Arduino Controller Starting...");
   Serial.println("Supports 1-4 feeders dynamically");

   // Initialize Motor Shield
   Serial.println("Initializing motor shield...");
   if (!AFMS.begin()) {
     Serial.println("ERROR:Motor shield not found - check I2C connections");
     Serial.println("ERROR:Make sure motor shield is properly seated on Arduino");
     while (1);  // Stop execution
   }
   Serial.println("✓ Motor shield initialized successfully");
   Serial.println("✓ I2C communication working");

   // Initialize all 4 motors
   motor1->setSpeed(0);
   motor1->run(RELEASE);
   motor2->setSpeed(0);
   motor2->run(RELEASE);
   motor3->setSpeed(0);
   motor3->run(RELEASE);
   motor4->setSpeed(0);
   motor4->run(RELEASE);

   // Initialize motor state array
   motors[0] = {false, 0, 0, motor1, false, 0, 255};
   motors[1] = {false, 0, 0, motor2, false, 0, 255};
   motors[2] = {false, 0, 0, motor3, false, 0, 255};
   motors[3] = {false, 0, 0, motor4, false, 0, 255};

  // Setup Timer1 for 1ms interrupts (1000 Hz)
  setup_timer_interrupt();

   // Initialize all beam break pins
   for (int i = 0; i < 4; i++) {
     pinMode(BEAM_BREAK_PINS[i], INPUT_PULLUP);
   }
   pinMode(TTL_INPUT_PIN, INPUT_PULLUP);
   pinMode(TTL_OUTPUT_PIN, OUTPUT);
   pinMode(LED_PIN, OUTPUT);

   digitalWrite(TTL_OUTPUT_PIN, LOW);
   digitalWrite(LED_PIN, HIGH);  // Status LED on

   Serial.println("Arduino ready for commands");
   Serial.println("Configured for up to 4 feeders (0-3)");
   delay(100);
 }

 void loop() {
  // Process timer interrupt flag FIRST for immediate motor response
  if (timer_interrupt_flag) {
    timer_interrupt_flag = false;
    update_motors_interrupt();
  }

  // Handle Serial Commands
  handle_serial_commands();

  // Get current time for sensor checks
  unsigned long current_time = millis();

  // Check Beam Breaks (less frequent)
  if (current_time - last_beam_check >= BEAM_CHECK_INTERVAL) {
    check_beam_breaks();
    last_beam_check = current_time;
  }

  // Check TTL Input (less frequent)
  if (current_time - last_ttl_check >= TTL_CHECK_INTERVAL) {
    check_ttl_input();
    last_ttl_check = current_time;
  }
}

 void handle_serial_commands() {
   while (Serial.available()) {
     char c = Serial.read();

     if (c == '\n' || c == '\r') {
       if (input_buffer.length() > 0) {
         process_command(input_buffer);
         input_buffer = "";
       }
     } else {
       input_buffer += c;
     }
   }
 }

 void process_command(String command) {
  command.trim();

  // Parse MOTOR:feeder_id:duration_ms:speed
  if (command.startsWith("MOTOR:")) {
    // Find colons for parsing
    int first_colon = command.indexOf(':', 6);   // After "MOTOR:"
    int second_colon = command.indexOf(':', first_colon + 1);  // After feeder_id

    if (first_colon != -1 && second_colon != -1) {
      // Extract feeder_id, duration_ms, and speed
      int feeder_id = command.substring(6, first_colon).toInt();
      int duration_ms = command.substring(first_colon + 1, second_colon).toInt();
      int speed = command.substring(second_colon + 1).toInt();

      Serial.print("Parsed: feeder_id=");
      Serial.print(feeder_id);
      Serial.print(", duration_ms=");
      Serial.print(duration_ms);
      Serial.print(", speed=");
      Serial.println(speed);

      activate_motor(feeder_id, duration_ms, speed);
    } else if (first_colon != -1) {
      // Backward compatibility: MOTOR:feeder_id:duration_ms (default speed 255)
      int feeder_id = command.substring(6, first_colon).toInt();
      int duration_ms = command.substring(first_colon + 1).toInt();

      Serial.print("Parsed (legacy): feeder_id=");
      Serial.print(feeder_id);
      Serial.print(", duration_ms=");
      Serial.print(duration_ms);
      Serial.println(", speed=255 (default)");

      activate_motor(feeder_id, duration_ms, 255);
    } else {
      Serial.println("ERROR:Invalid motor command format");
    }
  } else {
    Serial.println("ERROR:Unknown command");
  }
}

 void activate_motor(int feeder_id, int duration_ms, int speed) {
  // Validate feeder ID (0-3 for up to 4 feeders)
  if (feeder_id < 0 || feeder_id > 3) {
    Serial.print("ERROR:Invalid feeder ID (");
    Serial.print(feeder_id);
    Serial.println(") - must be 0-3");
    return;
  }

  if (duration_ms <= 0 || duration_ms > 10000) {  // Max 10 seconds
    Serial.println("ERROR:Invalid duration");
    return;
  }

  if (speed < 0 || speed > 255) {
    Serial.println("ERROR:Invalid speed (0-255)");
    return;
  }

  // Stop motor if already running
  if (motors[feeder_id].running) {
    motors[feeder_id].motor->run(RELEASE);
  }

  // Start motor with debugging
  Serial.print("DEBUG: Activating motor ");
  Serial.print(feeder_id);
  Serial.println(" now...");

  motors[feeder_id].motor->setSpeed(speed);  // Set requested speed
  motors[feeder_id].motor->run(FORWARD);

  // Set absolute target time instead of start time + duration
  noInterrupts();  // Atomic read of interrupt counter
  unsigned long current_counter = interrupt_counter;
  motor_target_times[feeder_id] = current_counter + duration_ms;
  interrupts();

  motors[feeder_id].running = true;
  motors[feeder_id].start_time = current_counter;  // Use interrupt counter for consistency
  motors[feeder_id].duration = duration_ms;
  motors[feeder_id].speed = speed;  // Store speed for debugging
  motors[feeder_id].stop_requested = false;

  Serial.print("DEBUG: Motor ");
  Serial.print(feeder_id);
  Serial.print(" activated for ");
  Serial.print(duration_ms);
  Serial.print("ms at speed ");
  Serial.print(speed);
  Serial.print(", target_time=");
  Serial.print(motor_target_times[feeder_id]);
  Serial.print(", current_counter=");
  Serial.println(current_counter);

  // Report motor activation to PC with Arduino timestamp in microseconds
  unsigned long timestamp_us = micros();
  Serial.print("MOTOR_START:");
  Serial.print(feeder_id);
  Serial.print(":");
  Serial.print(duration_ms);
  Serial.print(":");
  Serial.print(speed);
  Serial.print(":");
  Serial.println(timestamp_us);  // Send timestamp in microseconds
}

 // Timer1 interrupt service routine (called every 1ms)
ISR(TIMER1_COMPA_vect) {
  interrupt_counter++;

  // Check all 4 motors every 1ms for precise timing
  for (int i = 0; i < 4; i++) {
    if (motors[i].running && !motors[i].stop_requested) {
      // Use absolute target time instead of elapsed calculation
      if (interrupt_counter >= motor_target_times[i]) {
        // FLAG FOR IMMEDIATE STOP - don't call motor commands in interrupt
        motors[i].stop_requested = true;
        timer_interrupt_flag = true;  // Signal main loop for immediate processing

        // DEBUG: Record exact interrupt timing
        motors[i].actual_stop_time = interrupt_counter;
      }
    }
  }
}

// Setup Timer1 for 1ms interrupts
void setup_timer_interrupt() {
  noInterrupts();  // Disable interrupts during setup

  // Clear Timer1 registers
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;

  // Set compare match register for 1ms intervals
  // 16MHz / (64 * 1000Hz) - 1 = 249
  OCR1A = 249;

  // Set CTC mode (Clear Timer on Compare Match)
  TCCR1B |= (1 << WGM12);

  // Set prescaler to 64
  TCCR1B |= (1 << CS11) | (1 << CS10);

  // Enable timer compare interrupt
  TIMSK1 |= (1 << OCIE1A);

  interrupts();  // Re-enable interrupts

  Serial.println("✓ Timer interrupt setup complete (1ms precision)");
}

// Process motor stops immediately when flagged by interrupt
void update_motors_interrupt() {
  for (int i = 0; i < 4; i++) {
    if (motors[i].running && motors[i].stop_requested) {
      // STOP MOTOR IMMEDIATELY
      motors[i].motor->run(RELEASE);
      motors[i].running = false;

      // Calculate actual duration using interrupt timing (1ms precision)
      unsigned long actual_duration = motors[i].actual_stop_time - motors[i].start_time;

      // Clear the stop request flag
      motors[i].stop_requested = false;

      Serial.print("DEBUG: Motor ");
      Serial.print(i);
      Serial.print(" stopped after ");
      Serial.print(actual_duration);
      Serial.print("ms (target was ");
      Serial.print(motors[i].duration);
      Serial.print("ms, error: ");
      Serial.print((long)actual_duration - (long)motors[i].duration);
      Serial.print("ms) [start=");
      Serial.print(motors[i].start_time);
      Serial.print(", stopped_at=");
      Serial.print(motors[i].actual_stop_time);
      Serial.print(", target=");
      Serial.print(motor_target_times[i]);
      Serial.println("]");

      // Report motor stop to PC with Arduino timestamp in microseconds
      unsigned long timestamp_us = micros();
      Serial.print("MOTOR_STOP:");
      Serial.print(i);
      Serial.print(":");
      Serial.println(timestamp_us);  // Send timestamp in microseconds
    }
  }
}

 void check_beam_breaks() {
   // Check all 4 feeders dynamically
   for (int i = 0; i < 4; i++) {
     bool current_state = digitalRead(BEAM_BREAK_PINS[i]);
     if (beam_break_state[i] == HIGH && current_state == LOW) {
       // Beam broken (HIGH to LOW transition)
       // Send with Arduino timestamp in microseconds
       unsigned long timestamp_us = micros();

       Serial.print("BEAM:");
       Serial.print(i);
       Serial.print(":");
       Serial.println(timestamp_us);

       // Blink LED to indicate detection
       digitalWrite(LED_PIN, LOW);
       delay(50);
       digitalWrite(LED_PIN, HIGH);
     }
     beam_break_state[i] = current_state;
   }
 }

 void check_ttl_input() {
   bool current_ttl = digitalRead(TTL_INPUT_PIN);

   // Detect rising edge (LOW to HIGH transition)
   if (ttl_input_state == LOW && current_ttl == HIGH) {
     // Send with Arduino timestamp in microseconds
     unsigned long timestamp_us = micros();

     Serial.print("TTL:");
     Serial.println(timestamp_us);
     // Don't echo TTL to output - just report to PC
   }

   ttl_input_state = current_ttl;
 }

 void send_ttl_pulse() {
   digitalWrite(TTL_OUTPUT_PIN, HIGH);
   delay(50);  // 50ms pulse width
   digitalWrite(TTL_OUTPUT_PIN, LOW);
 }

 /*
  * Installation Notes:
  *
  * 1. Install Adafruit Motor Shield V3 Library:
  *    - In Arduino IDE: Sketch > Include Library > Manage Libraries
  *    - Search for "Adafruit Motor Shield V2 Library" and install
  *    - Also install "Adafruit Bus IO" if prompted
  *
  * 2. Wiring:
  *    - Motors: Connect to M1, M2, M3, M4 terminals on motor shield
  *    - Beam Break Sensors:
  *      * Feeder 0 sensor to pin 2
  *      * Feeder 1 sensor to pin 3
  *      * Feeder 2 sensor to pin 6
  *      * Feeder 3 sensor to pin 7
  *      * Connect sensor VCC to 5V, GND to GND
  *    - TTL Input: Connect to pin 4 (for external sync)
  *    - TTL Output: Connect to pin 5 (for outgoing sync signals)
  *
  * 3. Testing:
  *    - Upload code to Arduino
  *    - Open Serial Monitor at 9600 baud
  *    - Send commands like: MOTOR:0:500:255
  *    - Send commands for any feeder 0-3: MOTOR:2:500:255
  *    - Should see beam break messages when sensors are triggered
  *
  * 4. Motor Shield Setup:
  *    - Ensure motor shield is properly seated on Arduino
  *    - Connect external power supply to motor shield if using high-power motors
  *    - Default I2C address is used (0x60)
  *
  * 5. Scalability:
  *    - Supports 1-4 feeders dynamically
  *    - Works regardless of how many feeders are physically connected
  *    - Just connect the feeders you need (1, 2, 3, or 4)
  *    - Unused feeders will simply not receive commands
  */