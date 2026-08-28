package com.eurosa.bank.customerpreferenceservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "customer_preferences")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerPreference {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
