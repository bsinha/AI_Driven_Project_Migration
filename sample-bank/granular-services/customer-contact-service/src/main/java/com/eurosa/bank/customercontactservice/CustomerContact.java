package com.eurosa.bank.customercontactservice;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "customer_contacts")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerContact {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
}
